from . import db
from enum import Enum
from datetime import datetime
from flask_login import UserMixin


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELED = "canceled"


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
    plan_type = db.Column(db.String(20), default='Free')
    plan_start_date = db.Column(db.DateTime)
    plan_end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def name(self):
        return self.fullname

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

    user = db.relationship('User', backref=db.backref('bookings', lazy=True))

    def __repr__(self):
        return f'<Booking {self.booking_reference}>'
