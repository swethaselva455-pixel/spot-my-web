import secrets
from datetime import datetime, timedelta, timezone
from config import Config
from models import db, Service, Slot, Booking
from services.availability import is_slot_available_for_booking, release_expired_holds

def generate_reference_code():
    # Generate an alphanumeric booking reference code with business prefix.
    suffix = secrets.token_hex(3).upper()
    return f"SMS-{suffix}"

def create_checkout_hold(service_id, slot_id, customer_name, customer_email, customer_phone):
    # Validate slot availability, compute taxes, and reserve slot with 10-minute hold lock.
    release_expired_holds()
    
    available, message = is_slot_available_for_booking(slot_id)
    if not available:
        return False, message, None

    service = db.session.get(Service, service_id)
    slot = db.session.get(Slot, slot_id)
    if not service or not slot:
        return False, "Invalid service or slot selection.", None

    subtotal = round(float(service.price), 2)
    tax_amount = round(subtotal * (Config.TAX_PERCENT / 100.0), 2)
    total_amount = round(subtotal + tax_amount, 2)

    now_utc = datetime.now(timezone.utc)
    hold_expires = now_utc + timedelta(minutes=Config.SLOT_HOLD_MINUTES)

    booking = Booking(
        booking_reference=generate_reference_code(),
        service_id=service.id,
        slot_id=slot.id,
        customer_name=customer_name.strip(),
        customer_email=customer_email.strip().lower(),
        customer_phone=customer_phone.strip(),
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        status='pending',
        hold_expires_at=hold_expires
    )
    db.session.add(booking)
    db.session.commit()
    return True, "Hold reserved successfully.", booking

def get_booking_details(reference):
    # Retrieve booking details along with remaining countdown seconds for checkout.
    release_expired_holds()
    booking = Booking.query.filter_by(booking_reference=reference).first()
    if not booking:
        return None, 0

    remaining_seconds = 0
    if booking.status == 'pending' and booking.hold_expires_at:
        now_utc = datetime.now(timezone.utc)
        exp = booking.hold_expires_at.replace(tzinfo=timezone.utc) if booking.hold_expires_at.tzinfo is None else booking.hold_expires_at
        diff = (exp - now_utc).total_seconds()
        remaining_seconds = max(0, int(diff))
        if remaining_seconds <= 0:
            booking.status = 'cancelled'
            booking.cancellation_reason = 'Checkout hold expired'
            db.session.commit()

    return booking, remaining_seconds
