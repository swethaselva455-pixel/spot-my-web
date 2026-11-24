from datetime import datetime, timezone
from config import Config
from models import db, Booking, Payment
from services.payment_service import refund_payment

def calculate_refund_preview(booking):
    # Calculate eligible refund amount and policy tier based on time remaining before shoot slot.
    if not booking or not booking.slot:
        return 0.0, "Invalid booking."

    slot_date = booking.slot.slot_date
    try:
        start_t = datetime.strptime(booking.slot.start_time, "%H:%M").time()
    except Exception:
        start_t = datetime.strptime("09:00", "%H:%M").time()

    appointment_dt = datetime.combine(slot_date, start_t).replace(tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    hours_remaining = (appointment_dt - now_utc).total_seconds() / 3600.0

    if hours_remaining >= Config.FULL_REFUND_HOURS_BEFORE:
        refund_amount = round(booking.total_amount, 2)
        policy_label = f"100% Full Refund (Cancelled {int(hours_remaining)}h in advance; requirement is >= {Config.FULL_REFUND_HOURS_BEFORE}h)"
    elif hours_remaining > 0:
        refund_amount = round(booking.total_amount * (Config.PARTIAL_REFUND_PERCENT / 100.0), 2)
        policy_label = f"{int(Config.PARTIAL_REFUND_PERCENT)}% Partial Refund (Cancelled within {Config.FULL_REFUND_HOURS_BEFORE}h of start time)"
    else:
        refund_amount = 0.0
        policy_label = "0% Refund (Shoot time has already begun or passed)"

    return refund_amount, policy_label

def cancel_customer_booking(booking_reference, customer_email, reason="Customer cancelled via portal"):
    # Authenticate booking reference and customer email, process refund, and reopen slot.
    booking = Booking.query.filter(
        Booking.booking_reference == booking_reference.strip().upper(),
        Booking.customer_email == customer_email.strip().lower()
    ).first()

    if not booking:
        return False, "No matching booking found for this reference and email.", None

    if booking.status == 'cancelled':
        return False, "This booking has already been cancelled.", booking

    paid_payment = Payment.query.filter_by(booking_id=booking.id, status='paid').first()
    refund_amount = 0.0
    refund_id = None

    if booking.status == 'confirmed' and paid_payment:
        refund_amount, policy_info = calculate_refund_preview(booking)
        if refund_amount > 0:
            success, ref_msg, refund_id = refund_payment(paid_payment, refund_amount)
            if not success:
                return False, f"Cancellation halted because refund failed: {ref_msg}", booking
    elif booking.status == 'pending':
        refund_amount = 0.0

    booking.status = 'cancelled'
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.cancellation_reason = reason
    booking.refund_amount = refund_amount
    booking.hold_expires_at = None
    db.session.commit()

    return True, f"Booking successfully cancelled. Refund processed: {Config.CURRENCY_SYMBOL}{refund_amount:.2f}", booking

def admin_cancel_booking(booking_id, refund_percentage=100.0, reason="Admin manual cancellation"):
    # Allow administrators to manually cancel a booking with custom refund percentage.
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.status == 'cancelled':
        return False, "Booking not found or already cancelled.", None

    paid_payment = Payment.query.filter_by(booking_id=booking.id, status='paid').first()
    refund_amount = round(booking.total_amount * (float(refund_percentage) / 100.0), 2)
    refund_id = None

    if paid_payment and refund_amount > 0:
        success, ref_msg, refund_id = refund_payment(paid_payment, refund_amount)
        if not success:
            return False, f"Refund failure: {ref_msg}", booking

    booking.status = 'cancelled'
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.cancellation_reason = reason
    booking.refund_amount = refund_amount
    booking.hold_expires_at = None
    db.session.commit()

    return True, f"Admin cancelled booking. Refund of {Config.CURRENCY_SYMBOL}{refund_amount:.2f} issued.", booking
