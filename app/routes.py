from flask import Blueprint, request, jsonify, session, flash, render_template, url_for, redirect, get_flashed_messages, current_app
from .forms import LoginForm, SignupForm
from .models import db, ParkingSpot, Booking, User, BookingStatus, PaymentStatus, Payment, PaymentLog
from .services.mpesa_service import MpesaService
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
import random
import string
import logging
import json


main = Blueprint('main', __name__)

INACTIVITY_TIMEOUT = timedelta(minutes=15)


def is_session_active():
    """ Check if user session is active or expired """
    last_activity = session.get('last_activity')
    if last_activity:
        elapsed_time = datetime.utcnow() - datetime.fromtimestamp(last_activity)
        if elapsed_time > INACTIVITY_TIMEOUT:
            session.clear()  # Logout user
            flash("You have been logged out due to inactivity.", "info")
            return False
    session['last_activity'] = datetime.utcnow(
    ).timestamp()
    return True


@main.before_request
def check_session():
    """ Automatically logout inactive users """
    if 'user_id' in session and not is_session_active():
        return redirect(url_for('main.login'))


@main.route('/')
def home():
    print("Session Data:", session)
    user = None
    user_id = session.get("user_id")

    if user_id:
        user = User.query.get(user_id)
        print("Retrieved User:", user)

    return render_template('index.html', user=user)


@main.route('/about')
def about():
    return render_template('about.html')


@main.route('/plans')
def plans():
    return render_template('plans.html')


@main.route('/testimonials')
def testimonials():
    return render_template('testimonials.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(username=form.username.data).first()

            if not user or not check_password_hash(user.password, form.password.data):
                flash('Invalid credentials. Please try again.', 'danger')
                return redirect(url_for('main.login'))

            session['user_id'] = user.id
            session.permanent = True
            session.modified = True
            session['last_activity'] = datetime.utcnow().timestamp()
            flash('Login successful! Welcome back.', 'success')
            return redirect(url_for('main.home'))
        except SQLAlchemyError as e:
            current_app.logger.error(f"Database error during login: {str(e)}")
            flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('main.login'))
        except Exception as e:
            current_app.logger.error(
                f"Unexpected error during login: {str(e)}")
            flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('main.login'))

    # Show validation errors if form submission failed
    if request.method == "POST" and form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
        current_app.logger.warning(
            f"Login form validation failed: {form.errors}")

    return render_template('login.html', form=form)


@main.route('/logout')
def logout():
    """ Handle user logout """
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('main.login'))


@main.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        try:
            existing_user_email = User.query.filter_by(
                email=form.email.data).first()
            existing_user_username = User.query.filter_by(
                username=form.username.data).first()

            if existing_user_email:
                flash(
                    'Email is already registered. Please use a different one or log in.', 'danger')
                return redirect(url_for('main.signup'))

            if existing_user_username:
                flash(
                    'Username is already taken. Please choose a different one.', 'danger')
                return redirect(url_for('main.signup'))

            hashed_password = generate_password_hash(form.password.data)
            new_user = User(
                fullname=form.fullname.data,
                username=form.username.data,
                email=form.email.data,
                password=hashed_password
            )
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('main.login'))
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error during signup: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('main.signup'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error during signup: {str(e)}")
            flash('An unexpected error occurred. Please try again.', 'danger')
            return redirect(url_for('main.signup'))

    if request.method == "POST":
        flash('Signup failed. Please check your details and try again.', 'warning')

    return render_template('signup.html', form=form)


@main.route('/api/parking-spots', methods=['GET'])
def get_parking_spots():
    """Get all parking spots with availability info"""
    try:
        check_in_date = request.args.get('check_in_date')
        check_in_time = request.args.get('check_in_time')
        check_out_date = request.args.get('check_out_date')
        check_out_time = request.args.get('check_out_time')

        spots = ParkingSpot.query.all()
        spots_list = []

        for spot in spots:
            spot_data = {
                'id': spot.id,
                'name': spot.name,
                'location': spot.location,
                'total_slots': spot.total_slots,
                'hourly_rate': spot.hourly_rate,
                'daily_rate': spot.daily_rate,
                'security_features': spot.security_features,
                'amenities': spot.amenities
            }

            # Add availability if date/time provided
            if all([check_in_date, check_in_time, check_out_date, check_out_time]):
                available_slots = spot.check_availability(
                    check_in_date, check_in_time, check_out_date, check_out_time)
                estimated_price = spot.calculate_price(
                    check_in_date, check_in_time, check_out_date, check_out_time)
                spot_data.update({
                    'available_slots': available_slots,
                    'estimated_price': estimated_price,
                    'is_available': available_slots > 0
                })
            else:
                spot_data['available_slots'] = spot.available_slots

            spots_list.append(spot_data)

        return jsonify(spots_list)
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error fetching parking spots: {str(e)}")
        return jsonify({'error': 'Failed to fetch parking spots'}), 500
    except ValueError as e:
        current_app.logger.error(f"Value error in parking spots: {str(e)}")
        return jsonify({'error': 'Invalid date or time format'}), 400
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error fetching parking spots: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@main.route('/api/check-availability', methods=['POST'])
def check_availability():
    """Check availability for specific parking spot and time"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400

        location_id = data.get('location_id')
        check_in_date = data.get('check_in_date')
        check_in_time = data.get('check_in_time')
        check_out_date = data.get('check_out_date')
        check_out_time = data.get('check_out_time')

        if not all([location_id, check_in_date, check_in_time, check_out_date, check_out_time]):
            return jsonify({'error': 'Missing required fields'}), 400

        spot = ParkingSpot.query.get(location_id)
        if not spot:
            return jsonify({'error': 'Parking spot not found'}), 404

        available_slots = spot.check_availability(
            check_in_date, check_in_time, check_out_date, check_out_time)
        estimated_price = spot.calculate_price(
            check_in_date, check_in_time, check_out_date, check_out_time)

        return jsonify({
            'available_slots': available_slots,
            'is_available': available_slots > 0,
            'estimated_price': estimated_price,
            'hourly_rate': spot.hourly_rate,
            'daily_rate': spot.daily_rate
        })
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error checking availability: {str(e)}")
        return jsonify({'error': 'Failed to check availability'}), 500
    except ValueError as e:
        current_app.logger.error(
            f"Value error checking availability: {str(e)}")
        return jsonify({'error': 'Invalid date or time format'}), 400
    except AttributeError as e:
        current_app.logger.error(
            f"Attribute error checking availability: {str(e)}")
        return jsonify({'error': 'Invalid parking spot data'}), 500
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error checking availability: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@main.route('/api/book', methods=['POST'])
def book():
    """Create a new parking booking"""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to make a booking'}), 401

    data = request.get_json()
    location_id = data.get('location_id')
    check_in_date = data.get('check_in_date')
    check_in_time = data.get('check_in_time')
    check_out_date = data.get('check_out_date')
    check_out_time = data.get('check_out_time')
    promo_code = data.get('promo_code', '')

    if not all([location_id, check_in_date, check_in_time, check_out_date, check_out_time]):
        return jsonify({'error': 'Missing required booking information'}), 400

    # Validate parking spot exists
    spot = ParkingSpot.query.get(location_id)
    if not spot:
        return jsonify({'error': 'Parking spot not found'}), 404

    # Check availability
    available_slots = spot.check_availability(
        check_in_date, check_in_time, check_out_date, check_out_time)
    if available_slots <= 0:
        return jsonify({'error': 'No slots available for the selected time period'}), 400

    # Calculate price
    total_price = spot.calculate_price(
        check_in_date, check_in_time, check_out_date, check_out_time)

    # Apply promo code discount if valid
    if promo_code:
        discount = apply_promo_code(promo_code, total_price)
        total_price = total_price * (1 - discount)

    # Generate booking reference
    booking_reference = 'EP' + \
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # Create booking with PENDING_PAYMENT status
    try:
        new_booking = Booking(
            user_id=session['user_id'],
            location_id=location_id,
            check_in_date=check_in_date,
            check_in_time=check_in_time,
            check_out_date=check_out_date,
            check_out_time=check_out_time,
            promo_code=promo_code,
            total_price=total_price,
            booking_reference=booking_reference,
            status=BookingStatus.PENDING.value,
            payment_status=PaymentStatus.PENDING.value,
            payment_attempts=0
        )

        db.session.add(new_booking)
        db.session.commit()

        current_app.logger.info(
            f"Booking created: {booking_reference} for user {session['user_id']}")

        # Return booking info - frontend will initiate payment
        return jsonify({
            'success': True,
            'message': 'Booking created. Please complete payment.',
            'booking_id': new_booking.id,
            'booking_reference': booking_reference,
            'total_price': total_price,
            'parking_spot': spot.name,
            'location': spot.location,
            'requires_payment': True
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error creating booking: {str(e)}")
        return jsonify({'error': 'Booking failed. Please try again.'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Unexpected error creating booking: {str(e)}")
        return jsonify({'error': 'Booking failed. Please try again.'}), 500


def apply_promo_code(promo_code, total_price):
    """Apply promo code discount"""
    promo_codes = {
        'FIRST10': 0.10,    # 10% off
        'STUDENT15': 0.15,  # 15% off for students
        'WEEKEND20': 0.20,  # 20% off for weekends
        'LOYAL25': 0.25     # 25% off for loyal customers
    }

    return promo_codes.get(promo_code.upper(), 0)


@main.route('/api/bookings', methods=['GET'])
def get_user_bookings():
    """Get current user's bookings"""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401

    try:
        bookings = Booking.query.filter_by(user_id=session['user_id']) \
            .options(joinedload(Booking.parking_spot)) \
            .order_by(Booking.created_at.desc()).all()

        bookings_list = []
        for booking in bookings:
            bookings_list.append({
                'id': booking.id,
                'booking_reference': booking.booking_reference,
                'parking_spot': booking.parking_spot.name,
                'location': booking.parking_spot.location,
                'check_in_date': booking.check_in_date,
                'check_in_time': booking.check_in_time,
                'check_out_date': booking.check_out_date,
                'check_out_time': booking.check_out_time,
                'total_price': booking.total_price,
                'status': booking.status,
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify(bookings_list)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error fetching bookings: {str(e)}")
        return jsonify({'error': 'Failed to fetch bookings'}), 500
    except AttributeError as e:
        current_app.logger.error(f"Attribute error in bookings: {str(e)}")
        return jsonify({'error': 'Invalid booking data'}), 500
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error fetching bookings: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@main.route('/api/user-info')
def user_info():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"name": user.fullname})
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error fetching user info: {str(e)}")
        return jsonify({"error": "Failed to fetch user information"}), 500
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error fetching user info: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@main.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    try:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            flash('User account not found. Please log in again.', 'danger')
            session.clear()
            return redirect(url_for('main.login'))

        bookings = Booking.query.filter_by(user_id=user_id) \
            .options(joinedload(Booking.parking_spot)).all()

        return render_template('dashboard.html', user=user, bookings=bookings)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error loading dashboard: {str(e)}")
        flash('Failed to load dashboard. Please try again.', 'danger')
        return redirect(url_for('main.home'))
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error loading dashboard: {str(e)}")
        flash('An unexpected error occurred.', 'danger')
        return redirect(url_for('main.home'))


@main.route('/api/bookings/<int:booking_id>/status', methods=['PUT'])
def update_booking_status(booking_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        new_status = data.get("status")

        if new_status not in ["pending", "confirmed", "canceled"]:
            return jsonify({"error": "Invalid status"}), 400

        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        if booking.user_id != session['user_id']:
            return jsonify({"error": "Unauthorized to modify this booking"}), 403

        booking.status = new_status
        db.session.commit()

        return jsonify({
            "message": f"Booking status updated to {new_status}",
            "booking_id": booking.id,
            "status": booking.status
        }), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Database error updating booking status: {str(e)}")
        return jsonify({"error": "Failed to update booking status"}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Unexpected error updating booking status: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@main.route('/api/bookings/<int:booking_id>/cancel', methods=['PUT'])
def cancel_booking(booking_id):
    """Cancel a booking"""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401

    try:
        booking = Booking.query.filter_by(
            id=booking_id, user_id=session['user_id']).first()
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        if booking.status == BookingStatus.CANCELED.value:
            return jsonify({'error': 'Booking already canceled'}), 400

        # Check if booking can be canceled (e.g., not past check-in time)
        check_in_datetime = datetime.strptime(
            f"{booking.check_in_date} {booking.check_in_time}", "%Y-%m-%d %H:%M")
        if datetime.now() >= check_in_datetime:
            return jsonify({'error': 'Cannot cancel booking after check-in time'}), 400

        # Restore parking slot if booking was confirmed and paid
        if booking.status == BookingStatus.CONFIRMED.value and booking.payment_status == PaymentStatus.COMPLETED.value:
            parking_spot = booking.parking_spot
            if parking_spot:
                parking_spot.available_slots += 1
                current_app.logger.info(
                    f"Restored slot for {parking_spot.name}, now {parking_spot.available_slots} available")

        booking.status = BookingStatus.CANCELED.value
        db.session.commit()

        return jsonify({'message': 'Booking canceled successfully'})
    except ValueError as e:
        current_app.logger.error(
            f"Date parsing error in cancel booking: {str(e)}")
        return jsonify({'error': 'Invalid booking date format'}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error canceling booking: {str(e)}")
        return jsonify({'error': 'Failed to cancel booking'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Unexpected error canceling booking: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@main.route('/api/payment/initiate', methods=['POST'])
def initiate_payment():
    """Initiate M-Pesa payment for a booking"""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401

    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        phone_number = data.get('phone_number')

        if not booking_id or not phone_number:
            return jsonify({'error': 'Booking ID and phone number are required'}), 400

        # Get booking
        booking = Booking.query.filter_by(
            id=booking_id, user_id=session['user_id']).first()
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Check if booking is in correct status
        if booking.payment_status not in [PaymentStatus.PENDING.value, PaymentStatus.FAILED.value]:
            return jsonify({'error': f'Cannot initiate payment for booking with status {booking.payment_status}'}), 400

        # Format phone number
        user = User.query.get(session['user_id'])
        formatted_phone = user.format_phone_for_mpesa(phone_number)
        if not formatted_phone:
            return jsonify({'error': 'Invalid phone number format. Use 07XXXXXXXX or 2547XXXXXXXX'}), 400

        # Calculate amount (booking total price)
        amount = booking.total_price

        # Log payment attempt
        booking.payment_attempts = (booking.payment_attempts or 0) + 1
        booking.last_payment_attempt = datetime.utcnow()
        booking.payment_phone_number = formatted_phone

        # Create payment log entry
        payment_log = PaymentLog(
            booking_id=booking.id,
            event_type='INITIATE',
            status='PENDING',
            message=f'Payment initiation attempt {booking.payment_attempts}',
            request_data=json.dumps({
                'phone_number': formatted_phone,
                'amount': amount,
                'booking_reference': booking.booking_reference
            }),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:200]
        )
        db.session.add(payment_log)
        db.session.commit()

        # Initiate M-Pesa STK Push
        try:
            mpesa = MpesaService()
        except Exception as e:
            current_app.logger.error(
                f"Failed to initialize M-Pesa service: {str(e)}")
            payment_log.status = 'FAILED'
            payment_log.message = 'M-Pesa service not configured. Please contact support.'
            db.session.commit()
            return jsonify({
                'success': False,
                'error': 'Payment service not configured. Please contact support.'
            }), 503

        result = mpesa.stk_push(
            phone_number=formatted_phone,
            amount=amount,
            account_reference=booking.booking_reference,
            transaction_desc=f'EasyPark Booking {booking.booking_reference}'
        )

        if result['success']:
            # Update booking with M-Pesa request IDs
            booking.checkout_request_id = result['checkout_request_id']
            booking.merchant_request_id = result['merchant_request_id']
            booking.payment_status = PaymentStatus.PENDING.value

            # Update payment log
            payment_log.status = 'SUCCESS'
            payment_log.response_data = json.dumps(result)

            db.session.commit()

            current_app.logger.info(
                f"Payment initiated for booking {booking.booking_reference}")

            return jsonify({
                'success': True,
                'message': result['customer_message'],
                'checkout_request_id': result['checkout_request_id']
            }), 200
        else:
            # Update payment status to failed
            booking.payment_status = PaymentStatus.FAILED.value
            booking.payment_result_code = result.get('response_code', '')
            booking.payment_result_desc = result.get('error', '')

            # Update payment log
            payment_log.status = 'FAILED'
            payment_log.message = result.get(
                'error', 'Payment initiation failed')
            payment_log.response_data = json.dumps(result)

            db.session.commit()

            return jsonify({
                'success': False,
                'error': result.get('error', 'Payment initiation failed'),
                'provider_response': result.get('provider_response')
            }), result.get('status_code', 502)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Database error initiating payment: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Unexpected error initiating payment: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@main.route('/api/mpesa/callback', methods=['POST'])
def mpesa_callback():
    """Handle M-Pesa payment callback"""
    try:
        callback_data = request.get_json()
        current_app.logger.info(
            f"M-Pesa callback received: {json.dumps(callback_data)}")

        # Process callback
        mpesa = MpesaService()
        result = mpesa.process_callback(callback_data)

        checkout_request_id = result.get('checkout_request_id')
        if not checkout_request_id:
            current_app.logger.error("No checkout_request_id in callback")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Invalid callback data'}), 400

        # Find booking by checkout_request_id
        booking = Booking.query.filter_by(
            checkout_request_id=checkout_request_id).first()
        if not booking:
            current_app.logger.error(
                f"Booking not found for checkout_request_id: {checkout_request_id}")
            return jsonify({'ResultCode': 1, 'ResultDesc': 'Booking not found'}), 404

        # Log callback
        payment_log = PaymentLog(
            booking_id=booking.id,
            event_type='CALLBACK',
            status='SUCCESS' if result['success'] else 'FAILED',
            message=result.get('result_desc', ''),
            response_data=json.dumps(callback_data),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')[:200]
        )
        db.session.add(payment_log)

        if result['success']:
            # Payment successful
            booking.payment_status = PaymentStatus.COMPLETED.value
            booking.status = BookingStatus.CONFIRMED.value
            booking.mpesa_receipt_number = result.get('mpesa_receipt_number')
            booking.payment_date = result.get(
                'transaction_date') or datetime.utcnow()
            booking.payment_amount = result.get('amount')
            booking.payment_result_code = result.get('result_code')
            booking.payment_result_desc = result.get('result_desc')

            # Create payment record
            payment = Payment(
                booking_id=booking.id,
                mpesa_receipt_number=result.get('mpesa_receipt_number'),
                checkout_request_id=checkout_request_id,
                merchant_request_id=result.get('merchant_request_id'),
                amount=result.get('amount'),
                phone_number=result.get('phone_number'),
                transaction_date=result.get(
                    'transaction_date') or datetime.utcnow(),
                payment_type='MPESA_STK',
                status='COMPLETED',
                result_code=result.get('result_code'),
                result_desc=result.get('result_desc'),
                raw_callback_data=json.dumps(callback_data)
            )
            db.session.add(payment)

            # Reduce available slots
            parking_spot = booking.parking_spot
            if parking_spot and parking_spot.available_slots > 0:
                parking_spot.available_slots -= 1

            current_app.logger.info(
                f"Payment completed for booking {booking.booking_reference}")
        else:
            # Payment failed
            booking.payment_status = PaymentStatus.FAILED.value
            booking.payment_result_code = result.get('result_code')
            booking.payment_result_desc = result.get('result_desc')

            current_app.logger.warning(
                f"Payment failed for booking {booking.booking_reference}: {result.get('result_desc')}")

        db.session.commit()

        # Acknowledge callback
        return jsonify({'ResultCode': 0, 'ResultDesc': 'Accepted'}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Database error in M-Pesa callback: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Database error'}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing M-Pesa callback: {str(e)}")
        return jsonify({'ResultCode': 1, 'ResultDesc': 'Server error'}), 500


@main.route('/api/booking/<int:booking_id>/status', methods=['GET'])
def get_booking_payment_status(booking_id):
    """Get booking and payment status"""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401

    try:
        booking = Booking.query.options(joinedload(Booking.parking_spot)).filter_by(
            id=booking_id, user_id=session['user_id']).first()
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Query M-Pesa if payment is pending
        if booking.payment_status == PaymentStatus.PENDING.value and booking.checkout_request_id:
            mpesa = MpesaService()
            query_result = mpesa.query_payment_status(
                booking.checkout_request_id)

            if query_result['success']:
                # Update status based on query result
                status = query_result.get('status')
                if status == 'COMPLETED':
                    booking.payment_status = PaymentStatus.COMPLETED.value
                    booking.status = BookingStatus.CONFIRMED.value
                elif status in ['FAILED', 'CANCELLED']:
                    booking.payment_status = PaymentStatus.FAILED.value

                booking.payment_result_code = query_result.get('result_code')
                booking.payment_result_desc = query_result.get('result_desc')
                db.session.commit()

        return jsonify({
            'booking_id': booking.id,
            'booking_reference': booking.booking_reference,
            'status': booking.status,
            'payment_status': booking.payment_status,
            'payment_result_desc': booking.payment_result_desc,
            'total_price': booking.total_price,
            'parking_spot': {
                'name': booking.parking_spot.name,
                'location': booking.parking_spot.location
            } if booking.parking_spot else None,
            'check_in_date': booking.check_in_date,
            'check_in_time': booking.check_in_time,
            'check_out_date': booking.check_out_date,
            'check_out_time': booking.check_out_time
        }), 200

    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error getting booking status: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error getting booking status: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@main.route('/api/booking/<int:booking_id>/retry-payment', methods=['POST'])
def retry_payment(booking_id):
    """Retry payment for a failed booking"""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401

    try:
        data = request.get_json()
        phone_number = data.get('phone_number')

        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400

        booking = Booking.query.filter_by(
            id=booking_id, user_id=session['user_id']).first()
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Check if booking can retry payment
        if booking.payment_status not in [PaymentStatus.PENDING.value, PaymentStatus.FAILED.value]:
            return jsonify({'error': f'Cannot retry payment for booking with status {booking.payment_status}'}), 400

        # Check payment attempts limit
        if booking.payment_attempts and booking.payment_attempts >= 3:
            return jsonify({'error': 'Maximum payment attempts reached. Please create a new booking.'}), 400

        # Use the initiate_payment logic
        request_data = {'booking_id': booking_id, 'phone_number': phone_number}
        with current_app.test_request_context(json=request_data, method='POST'):
            return initiate_payment()

    except Exception as e:
        current_app.logger.error(f"Error retrying payment: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


def cleanup_expired_bookings():
    """
    Clean up bookings that have been pending payment for more than 10 minutes.
    This function should be called periodically (e.g., via a cron job or background task).
    """
    try:
        expiry_time = datetime.utcnow() - timedelta(minutes=10)

        # Find expired pending bookings
        expired_bookings = Booking.query.filter(
            Booking.payment_status == PaymentStatus.PENDING.value,
            Booking.created_at < expiry_time
        ).all()

        for booking in expired_bookings:
            booking.status = BookingStatus.CANCELED.value
            booking.payment_status = PaymentStatus.EXPIRED.value
            booking.payment_result_desc = 'Payment expired after 10 minutes'

            current_app.logger.info(
                f"Expired booking {booking.booking_reference} - no payment received")

        if expired_bookings:
            db.session.commit()
            current_app.logger.info(
                f"Cleaned up {len(expired_bookings)} expired bookings")

        return len(expired_bookings)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Database error cleaning up expired bookings: {str(e)}")
        return 0
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Unexpected error cleaning up expired bookings: {str(e)}")
        return 0


@main.route('/api/admin/cleanup-expired', methods=['POST'])
def trigger_cleanup():
    """
    Admin endpoint to manually trigger cleanup of expired bookings.
    In production, this should be secured with admin authentication.
    """
    try:
        count = cleanup_expired_bookings()
        return jsonify({
            'success': True,
            'message': f'Cleaned up {count} expired bookings'
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error triggering cleanup: {str(e)}")
        return jsonify({'error': 'Cleanup failed'}), 500
