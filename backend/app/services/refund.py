import datetime
import uuid
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.config import settings
from app.models.booking import Booking
from app.models.payment import Payment, Refund
from app.models.audit import AuditLog
from app.models.notification import Notification

def calculate_cancellation_refund(booking: Booking, cancelled_by: str = "customer") -> Dict[str, Any]:
    now_utc = datetime.datetime.utcnow()
    total_amount = booking.total_amount
    subtotal = booking.subtotal
    policy = (booking.property.cancellation_policy if booking.property else "moderate").lower()

    # Owner cancellation, rejection, or expired pending request -> 100% full refund
    if cancelled_by in ("owner", "rejection", "timeout", "admin"):
        return {
            "hours_until_shoot": 0.0,
            "cancellation_policy": policy,
            "refund_percentage": 100,
            "refund_amount": total_amount,
            "platform_fee_retained": 0,
            "message": "Full 100% refund initiated because shoot was cancelled/declined by owner or administrator."
        }

    # Customer initiated cancellation
    hours_left = (booking.start_datetime - now_utc).total_seconds() / 3600.0
    if hours_left < 0:
        return {
            "hours_until_shoot": round(hours_left, 1),
            "cancellation_policy": policy,
            "refund_percentage": 0,
            "refund_amount": 0,
            "platform_fee_retained": booking.platform_fee,
            "message": "Shoot start time has already passed. No refund is available."
        }

    pct = 0
    if policy == "flexible":
        if hours_left >= 24.0:
            pct = 100
        elif hours_left >= 6.0:
            pct = 50
        else:
            pct = 0
    elif policy == "strict":
        if hours_left >= 168.0: # 7 days
            pct = 50
        else:
            pct = 0
    else: # moderate default
        if hours_left >= 72.0:
            pct = 100
        elif hours_left >= 24.0:
            pct = 50
        else:
            pct = 0

    # Note on Platform Fee & GST in code comments:
    # On customer cancellation:
    # - If 100% refund: The rental subtotal and GST are refunded. The platform convenience fee is retained for processing unless full waiver applies.
    # - If 50% refund: 50% of the location rental subtotal is refunded.
    # - If 0% refund: No amount refunded.
    if pct == 100:
        refund_amount = subtotal + booking.gst_amount
        fee_retained = booking.platform_fee
    elif pct == 50:
        refund_amount = subtotal // 2
        fee_retained = total_amount - refund_amount
    else:
        refund_amount = 0
        fee_retained = total_amount

    return {
        "hours_until_shoot": round(hours_left, 1),
        "cancellation_policy": policy,
        "refund_percentage": pct,
        "refund_amount": refund_amount,
        "platform_fee_retained": fee_retained,
        "message": f"{policy.capitalize()} Policy: {pct}% refund ({round(hours_left, 1)} hrs before shoot)."
    }

def execute_booking_refund(
    db: Session,
    booking: Booking,
    refund_amount: int,
    reason: str,
    cancelled_by: str,
    actor_id: int
) -> Refund:
    payment = db.query(Payment).filter(
        Payment.booking_id == booking.id,
        Payment.status == "captured"
    ).order_by(Payment.id.desc()).first()

    # Razorpay refund id
    rzp_refund_id = f"rfnd_{uuid.uuid4().hex[:14]}"

    # If live Razorpay API keys are configured and payment ID is present, invoke refund API
    if (settings.RAZORPAY_KEY_ID and 
        not settings.RAZORPAY_KEY_ID.startswith("rzp_test_spotmyshoot") and 
        payment and payment.razorpay_payment_id):
        try:
            import httpx
            auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            res = httpx.post(
                f"https://api.razorpay.com/v1/payments/{payment.razorpay_payment_id}/refund",
                auth=auth,
                json={"amount": refund_amount * 100, "notes": {"reason": reason}},
                timeout=10.0
            )
            if res.status_code in (200, 201):
                rzp_refund_id = res.json().get("id", rzp_refund_id)
        except Exception:
            pass

    # Create refund record
    refund = Refund(
        payment_id=payment.id if payment else None,
        booking_id=booking.id,
        amount=refund_amount,
        razorpay_refund_id=rzp_refund_id,
        status="processed",
        reason=reason
    )
    db.add(refund)

    # Update booking status
    if cancelled_by == "customer":
        booking.status = "cancelled_by_customer"
    elif cancelled_by == "owner":
        booking.status = "cancelled_by_owner"
    elif cancelled_by == "rejection":
        booking.status = "rejected"
    else:
        booking.status = "refunded"

    booking.cancellation_reason = reason

    # Create audit log
    audit = AuditLog(
        actor_id=actor_id,
        action="booking_cancelled_refunded",
        entity="booking",
        entity_id=str(booking.id),
        meta={"refund_amount": refund_amount, "cancelled_by": cancelled_by, "reason": reason}
    )
    db.add(audit)

    # In-app notification to customer
    cust_note = Notification(
        user_id=booking.customer_id,
        booking_id=booking.id,
        channel="in_app",
        type="booking_cancelled",
        title=f"Booking {booking.booking_code} Cancelled",
        payload={
            "message": f"Your booking {booking.booking_code} was cancelled. Refund of Rs. {refund_amount:,} has been initiated.",
            "refund_amount": refund_amount
        },
        status="sent",
        sent_at=datetime.datetime.utcnow()
    )
    db.add(cust_note)

    # In-app notification to owner
    if booking.property and booking.property.owner_id:
        owner_note = Notification(
            user_id=booking.property.owner_id,
            booking_id=booking.id,
            channel="in_app",
            type="booking_cancelled",
            title=f"Booking {booking.booking_code} Cancelled",
            payload={
                "message": f"Booking {booking.booking_code} for {booking.property.name} has been cancelled. Time slot is now open."
            },
            status="sent",
            sent_at=datetime.datetime.utcnow()
        )
        db.add(owner_note)

    db.commit()
    db.refresh(refund)
    db.refresh(booking)
    return refund
