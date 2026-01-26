from . import db
from enum import Enum
from datetime import datetime
from flask_login import UserMixin


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELED = "canceled"


class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUND_REQUESTED = "refund_requested"
    REFUNDED = "refunded"


class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    bookings = db.relationship('Booking', backref='parking_spot', lazy=True)
    total_slots = db.Column(db.Integer, nullable=False, default=50)
    available_slots = db.Column(db.Integer, nullable=False, default=50)
    hourly_rate = db.Column(db.Float, nullable=False,
                            default=100.0)  # KES per hour
    daily_rate = db.Column(db.Float, nullable=False,
                           default=800.0)   # KES per day
    # CCTV, Security guards, etc.
    security_features = db.Column(db.String(500))
    amenities = db.Column(db.String(500))  # Covered, Electric charging, etc.

    def check_availability(self, check_in_date, check_in_time, check_out_date, check_out_time):
        """Check if slots are available for the requested time period"""
        try:
            # Parse the input dates and times
            check_in_datetime = datetime.strptime(
                f"{check_in_date} {check_in_time}", "%Y-%m-%d %H:%M")
            check_out_datetime = datetime.strptime(
                f"{check_out_date} {check_out_time}", "%Y-%m-%d %H:%M")

            # Find overlapping bookings
            overlapping_bookings = Booking.query.filter(
                Booking.location_id == self.id,
                Booking.status.in_(
                    [BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value])
            ).all()

            slots_occupied = 0
            for booking in overlapping_bookings:
                booking_start = datetime.strptime(
                    f"{booking.check_in_date} {booking.check_in_time}", "%Y-%m-%d %H:%M")
                booking_end = datetime.strptime(
                    f"{booking.check_out_date} {booking.check_out_time}", "%Y-%m-%d %H:%M")

                # Check if there's an overlap
                if (check_in_datetime < booking_end and check_out_datetime > booking_start):
                    slots_occupied += 1

            available = self.total_slots - slots_occupied
            return max(0, available)
        except ValueError:
            return 0

    def calculate_price(self, check_in_date, check_in_time, check_out_date, check_out_time):
        """Calculate the total price for the parking duration"""
        try:
            check_in_datetime = datetime.strptime(
                f"{check_in_date} {check_in_time}", "%Y-%m-%d %H:%M")
            check_out_datetime = datetime.strptime(
                f"{check_out_date} {check_out_time}", "%Y-%m-%d %H:%M")

            duration = check_out_datetime - check_in_datetime
            hours = duration.total_seconds() / 3600

            # If more than 8 hours, use daily rate
            if hours > 8:
                days = max(1, int(hours / 24))
                return days * self.daily_rate
            else:
                return max(1, int(hours)) * self.hourly_rate
        except ValueError:
            return 0

    def __repr__(self):
        return f'<ParkingSpot {self.name}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    # Format: 254712345678
    phone_number = db.Column(db.String(15), nullable=True)
    phone_verified = db.Column(db.Boolean, default=False)
    plan_type = db.Column(db.String(20), default='Free')
    plan_start_date = db.Column(db.DateTime)
    plan_end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def name(self):
        return self.fullname

    def format_phone_for_mpesa(self, phone_number=None):
        """Convert phone to M-Pesa format (254XXXXXXXXX)"""
        phone_to_format = phone_number or self.phone_number
        if not phone_to_format:
            return None

        # Remove spaces, dashes, etc.
        phone = ''.join(filter(str.isdigit, phone_to_format))

        # Convert to 254 format
        if phone.startswith('0'):
            return '254' + phone[1:]
        elif phone.startswith('254'):
            return phone
        elif phone.startswith('+254'):
            return phone[1:]
        else:
            return '254' + phone

    def __repr__(self):
        return f'<User {self.username}>'


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey(
        'parking_spot.id'), nullable=False)
    check_in_date = db.Column(db.String(10), nullable=False)
    check_in_time = db.Column(db.String(5), nullable=False)
    check_out_date = db.Column(db.String(10), nullable=False)
    check_out_time = db.Column(db.String(5), nullable=False)
    promo_code = db.Column(db.String(20))
    status = db.Column(db.String(10), nullable=False,
                       default=BookingStatus.PENDING.value)
    total_price = db.Column(db.Float, nullable=False, default=0.0)
    booking_reference = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # M-Pesa Payment Fields
    payment_status = db.Column(
        db.String(20), default=PaymentStatus.PENDING.value)
    payment_phone_number = db.Column(
        db.String(15), nullable=True)  # 254712345678
    checkout_request_id = db.Column(db.String(50), unique=True, nullable=True)
    merchant_request_id = db.Column(db.String(50), nullable=True)
    mpesa_receipt_number = db.Column(
        db.String(20), unique=True, nullable=True)  # e.g., NLJ7RT61SV
    payment_date = db.Column(db.DateTime, nullable=True)
    payment_amount = db.Column(db.Float, nullable=True)  # Amount actually paid
    payment_attempts = db.Column(db.Integer, default=0)
    last_payment_attempt = db.Column(db.DateTime, nullable=True)
    payment_result_code = db.Column(
        db.Integer, nullable=True)  # M-Pesa ResultCode
    payment_result_desc = db.Column(db.String(200), nullable=True)

    user = db.relationship('User', backref=db.backref('bookings', lazy=True))
    payments = db.relationship(
        'Payment', backref='booking', lazy=True, cascade='all, delete-orphan')
    payment_logs = db.relationship(
        'PaymentLog', backref='booking', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Booking {self.booking_reference}>'


class Payment(db.Model):
    """Separate table for payment transactions (better audit trail)"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey(
        'booking.id'), nullable=False)

    # M-Pesa Transaction Details
    mpesa_receipt_number = db.Column(
        db.String(20), unique=True, nullable=False)
    checkout_request_id = db.Column(db.String(50), unique=True, nullable=False)
    merchant_request_id = db.Column(db.String(50), nullable=True)

    # Payment Information
    amount = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False)

    # Status Tracking
    payment_type = db.Column(
        db.String(20), default='PAYMENT')  # 'PAYMENT', 'REFUND'
    # 'SUCCESS', 'FAILED', 'PENDING'
    status = db.Column(db.String(20), nullable=False)
    result_code = db.Column(db.Integer, nullable=True)
    result_desc = db.Column(db.String(200), nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Callback Data (store full JSON for debugging)
    raw_callback_data = db.Column(db.Text, nullable=True)  # Store JSON string

    def __repr__(self):
        return f'<Payment {self.mpesa_receipt_number}>'


class PaymentLog(db.Model):
    """Audit trail for all payment-related events"""
    __tablename__ = 'payment_logs'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey(
        'booking.id'), nullable=False)

    # Event Details
    # 'STK_PUSH_INITIATED', 'CALLBACK_RECEIVED', etc.
    event_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=True)

    # Request/Response Data
    request_data = db.Column(db.Text, nullable=True)  # JSON
    response_data = db.Column(db.Text, nullable=True)  # JSON

    # Metadata
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PaymentLog {self.event_type} - {self.created_at}>'
