import json
import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.booking import Booking
from app.models.payment import Payment
from app.schemas.payment import (
    CreateOrderRequest, CreateOrderResponse, VerifyPaymentRequest, PaymentOut
)
from app.utils.dependencies import get_current_user
from app.services.payment import (
    create_razorpay_order, verify_razorpay_signature,
    verify_webhook_signature, process_successful_payment
)
from app.services.notification import send_notification
from app.services.invoice import generate_invoice_pdf

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/create-order", response_model=CreateOrderResponse)
def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == body.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.customer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    if booking.status not in ("hold", "pending_owner"):
        raise HTTPException(status_code=400, detail=f"Booking is not awaiting payment (status: {booking.status}).")

    # Check hold expiry
    now_utc = datetime.datetime.utcnow()
    if booking.hold_expires_at and booking.hold_expires_at < now_utc:
        booking.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="Booking hold has expired. Please select a slot again.")

    order_data = create_razorpay_order(booking)

    # Save payment record with status 'created'
    existing = db.query(Payment).filter(Payment.razorpay_order_id == order_data["razorpay_order_id"]).first()
    if not existing:
        p = Payment(
            booking_id=booking.id,
            razorpay_order_id=order_data["razorpay_order_id"],
            amount=booking.total_amount,
            currency="INR",
            status="created"
        )
        db.add(p)
        db.commit()

    return CreateOrderResponse(**order_data)

@router.post("/verify")
def verify_payment(
    body: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == body.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.customer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    # Verify signature
    valid = verify_razorpay_signature(
        order_id=body.razorpay_order_id,
        payment_id=body.razorpay_payment_id,
        signature=body.razorpay_signature
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature. Transaction could not be verified.")

    # Process payment & update booking
    booking, payment = process_successful_payment(
        db=db,
        booking_id=booking.id,
        razorpay_order_id=body.razorpay_order_id,
        razorpay_payment_id=body.razorpay_payment_id,
        signature=body.razorpay_signature
    )

    # Generate invoice PDF
    try:
        pdf_path = generate_invoice_pdf(booking)
    except Exception:
        pdf_path = None

    # Notify customer
    send_notification(
        db=db,
        user_id=booking.customer_id,
        type_name="payment_success",
        title=f"Payment Confirmed for {booking.booking_code}",
        message=f"Your payment of Rs. {booking.total_amount:,} was successful! Status: {booking.status.replace('_', ' ').capitalize()}.",
        booking_id=booking.id,
        channel="in_app",
        attachment_path=pdf_path
    )

    # Notify owner of new booking request
    if booking.property and booking.property.owner_id:
        send_notification(
            db=db,
            user_id=booking.property.owner_id,
            type_name="booking_request",
            title=f"New Booking Request ({booking.booking_code})",
            message=f"You have a new paid booking request for {booking.property.name}. Please review and accept/decline.",
            booking_id=booking.id,
            channel="in_app"
        )

    return {
        "status": "success",
        "booking_id": booking.id,
        "booking_code": booking.booking_code,
        "booking_status": booking.status,
        "message": "Payment verified successfully!"
    }

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    raw_body = await request.body()
    
    # If a signature header is provided, verify it
    if x_razorpay_signature:
        if not verify_webhook_signature(raw_body, x_razorpay_signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        data = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON")

    event = data.get("event")
    payload = data.get("payload", {})

    if event == "payment.captured":
        payment_entity = payload.get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")
        method = payment_entity.get("method", "unknown")

        payment_rec = db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()
        if payment_rec:
            process_successful_payment(
                db=db,
                booking_id=payment_rec.booking_id,
                razorpay_order_id=order_id,
                razorpay_payment_id=payment_id,
                signature="webhook_verified",
                method=method
            )

    elif event == "payment.failed":
        payment_entity = payload.get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_rec = db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()
        if payment_rec:
            payment_rec.status = "failed"
            db.commit()

    return {"status": "ok"}
