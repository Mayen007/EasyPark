from flask import Blueprint, request, jsonify, session, flash, render_template, url_for, redirect, get_flashed_messages, current_app
from .forms import LoginForm, SignupForm
from .models import db, ParkingSpot, Booking, User, BookingStatus
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
import random
import string
import logging


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

    if request.method == "POST":
        flash('Login failed. Please check your details and try again.', 'warning')

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

    # Create booking
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
            status=BookingStatus.CONFIRMED.value
        )

        db.session.add(new_booking)
        db.session.commit()

        return jsonify({
            'message': 'Booking successful!',
            'booking_reference': booking_reference,
            'total_price': total_price,
            'parking_spot': spot.name,
            'location': spot.location
        })

    except Exception as e:
        db.session.rollback()
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
        bookings = Booking.query.filter_by(user_id=session['user_id']).order_by(
            Booking.created_at.desc()).all()

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

        bookings = Booking.query.filter_by(user_id=user_id).all()

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
