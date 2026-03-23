from datetime import datetime, date, time, timedelta, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Hall names as per requirement
HALL_NAMES = ['RD hall', 'Charles Babbage hall', 'Kailash hall', 'AV hall', 'IM hall']

# Default chair capacity per hall (admin can adjust via keywords/config if needed)
DEFAULT_HALL_CAPACITY = 200


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    # Username used for login (or email if preferred)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # Optional friendly name of the staff/admin (for display and emails)
    full_name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # NOTE: Stored only because admin requested viewing staff passwords in UI.
    # This is insecure for production use.
    password_plain = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(120), nullable=True)  # for notifications
    role = db.Column(db.String(20), default='staff')  # admin / staff
    # Store timestamps in UTC; display can convert to local time.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Hall(db.Model):
    __tablename__ = 'halls'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=DEFAULT_HALL_CAPACITY)  # total chairs


class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hall_id = db.Column(db.Integer, db.ForeignKey('halls.id'), nullable=False)
    department = db.Column(db.String(120), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    num_days = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    chairs_required = db.Column(db.Integer, nullable=False)
    guest_chairs = db.Column(db.Integer, nullable=False)
    faculties_count = db.Column(db.Integer, default=0)
    audio_system = db.Column(db.Boolean, default=False)
    microphones = db.Column(db.Integer, default=0)  # count
    mic_types = db.Column(db.String(200), default='')  # CSV: neck_band,hand,fixed
    photography = db.Column(db.Boolean, default=False)
    podium_required = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='pending')  # pending / approved / rejected / cancelled
    # Store timestamps in UTC; display can convert to local time.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)  # admin rejection/approval notes

    user = db.relationship('User', backref=db.backref('bookings', lazy=True))
    hall = db.relationship('Hall', backref=db.backref('bookings', lazy=True))

    @property
    def event_end_date(self) -> date:
        days = max(int(self.num_days or 1), 1)
        return self.booking_date + timedelta(days=days - 1)

    @property
    def created_at_local(self):
        """Return created_at converted to the server's local timezone for display."""
        if not self.created_at:
            return None
        dt = self.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone()


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))


class Block(db.Model):
    __tablename__ = 'blocks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class ClassGroup(db.Model):
    __tablename__ = 'class_groups'
    id = db.Column(db.Integer, primary_key=True)
    hall_id = db.Column(db.Integer, db.ForeignKey('halls.id'), nullable=False)
    block_id = db.Column(db.Integer, db.ForeignKey('blocks.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    hall = db.relationship('Hall', backref=db.backref('class_groups', lazy=True))
    block = db.relationship('Block', backref=db.backref('class_groups', lazy=True))


class Keyword(db.Model):
    __tablename__ = 'keywords'
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
