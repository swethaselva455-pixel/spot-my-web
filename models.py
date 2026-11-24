from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Service(db.Model):
    """Represents a bookable creative space or studio shoot service."""
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    duration_hours = db.Column(db.Integer, default=2)
    image_url = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    slots = db.relationship('Slot', backref='service', lazy=True)
    bookings = db.relationship('Booking', backref='service', lazy=True)

    @property
    def location_area(self):
        # Return city neighborhood associated with space category.
        mapping = {
            "Villa": "ECR, Chennai",
            "Studio": "T. Nagar, Chennai",
            "Beach & Outdoor": "Marina Beach Road, Chennai",
            "Garden": "Alwarpet, Chennai",
            "Heritage": "Adyar, Chennai",
            "Loft": "Velachery, Chennai"
        }
        return mapping.get(self.category, "Chennai, India")

    @property
    def gallery_images(self):
        # Return collection of showcase photography angles for detail view.
        return [
            self.image_url,
            "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=800&q=80"
        ]

    @property
    def amenities_list(self):
        # Return verified studio and production amenities.
        return ["Natural Daylight", "Vanity / Green Room", "Power Backup", "High-Speed WiFi", "Dedicated Parking", "Air Conditioned"]

    def to_dict(self):
        # Convert service model fields to a dictionary.
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'price': self.price,
            'duration_hours': self.duration_hours,
            'image_url': self.image_url,
            'is_active': self.is_active
        }


class Slot(db.Model):
    """Represents an availability time window for a specific date and service."""
    __tablename__ = 'slots'

    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    slot_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    capacity = db.Column(db.Integer, default=1)
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    bookings = db.relationship('Booking', backref='slot', lazy=True)

    def active_reservations_count(self):
        # Count confirmed bookings plus non-expired pending checkout holds for this slot.
        now_utc = datetime.now(timezone.utc)
        count = 0
        for b in self.bookings:
            if b.status == 'confirmed':
                count += 1
            elif b.status == 'pending' and b.hold_expires_at:
                hold_exp = b.hold_expires_at.replace(tzinfo=timezone.utc) if b.hold_expires_at.tzinfo is None else b.hold_expires_at
                if hold_exp > now_utc:
                    count += 1
        return count

    def is_available(self):
        # Check if the slot is unblocked and has remaining open capacity.
        if self.is_blocked:
            return False
        return self.active_reservations_count() < self.capacity

    def to_dict(self):
        # Serialize slot data including current real-time availability.
        return {
            'id': self.id,
            'service_id': self.service_id,
            'slot_date': self.slot_date.strftime('%Y-%m-%d'),
            'start_time': self.start_time,
            'end_time': self.end_time,
            'capacity': self.capacity,
            'is_blocked': self.is_blocked,
            'available': self.is_available(),
            'booked_count': self.active_reservations_count()
        }


class Booking(db.Model):
    """Represents a customer appointment with pricing, payment link, and hold timer."""
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(32), unique=True, nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    slot_id = db.Column(db.Integer, db.ForeignKey('slots.id'), nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False, index=True)
    customer_phone = db.Column(db.String(30), nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, confirmed, cancelled
    hold_expires_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    refund_amount = db.Column(db.Float, default=0.0)
    reminder_24h_sent = db.Column(db.Boolean, default=False)
    reminder_1h_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    payments = db.relationship('Payment', backref='booking', lazy=True)

    def is_hold_valid(self):
        # Verify if the 10-minute checkout reservation hold is still active.
        if self.status == 'confirmed':
            return True
        if self.status != 'pending' or not self.hold_expires_at:
            return False
        exp = self.hold_expires_at.replace(tzinfo=timezone.utc) if self.hold_expires_at.tzinfo is None else self.hold_expires_at
        return exp > datetime.now(timezone.utc)

    def to_dict(self):
        # Convert booking entity into a structured dictionary.
        return {
            'id': self.id,
            'booking_reference': self.booking_reference,
            'service_name': self.service.name if self.service else 'Service',
            'slot_date': self.slot.slot_date.strftime('%Y-%m-%d') if self.slot else '',
            'start_time': self.slot.start_time if self.slot else '',
            'end_time': self.slot.end_time if self.slot else '',
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'total_amount': self.total_amount,
            'status': self.status,
            'refund_amount': self.refund_amount
        }


class Payment(db.Model):
    """Represents a Razorpay transaction record with verification signatures."""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    razorpay_order_id = db.Column(db.String(100), nullable=True, index=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    razorpay_signature = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    status = db.Column(db.String(30), default='created')  # created, paid, failed, refunded
    refund_id = db.Column(db.String(100), nullable=True)
    error_description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        # Convert payment entity into a structured dictionary.
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'razorpay_order_id': self.razorpay_order_id,
            'razorpay_payment_id': self.razorpay_payment_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'refund_id': self.refund_id
        }


class AdminUser(db.Model):
    """Represents a system administrator with hashed password credentials."""
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        # Compute and store a secure hash of the admin password.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Validate the supplied cleartext password against the stored hash.
        return check_password_hash(self.password_hash, password)
