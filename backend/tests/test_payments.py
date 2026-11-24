import os
import hmac
import hashlib
import datetime
from app.config import settings
from app.models.property import Property
from app.models.booking import Booking
from app.models.payment import Payment
from app.services.payment import (
    create_razorpay_order, verify_razorpay_signature, process_successful_payment
)
from app.services.invoice import generate_invoice_pdf

def test_razorpay_signature_verification():
    order_id = "order_test_12345"
    payment_id = "pay_test_67890"

    msg = f"{order_id}|{payment_id}"
    valid_sig = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        msg.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    assert verify_razorpay_signature(order_id, payment_id, valid_sig) is True
    assert verify_razorpay_signature(order_id, payment_id, "invalid_signature_hex") is False

def test_payment_processing_and_invoice(db_session, test_owner, test_customer):
    prop = Property(
        owner_id=test_owner.id,
        name="Invoice Test Loft",
        city="Chennai",
        area="T. Nagar",
        address="100 GN Chetty Road",
        property_type="studio",
        hourly_price=2000,
        approval_status="approved",
        is_published=True
    )
    db_session.add(prop)
    db_session.commit()

    now_utc = datetime.datetime.utcnow()
    b = Booking(
        booking_code="#SMS-PAY1",
        property_id=prop.id,
        customer_id=test_customer.id,
        shoot_category="Fashion",
        start_datetime=now_utc + datetime.timedelta(days=3),
        end_datetime=now_utc + datetime.timedelta(days=3, hours=2),
        duration_hours=2,
        crew_size=4,
        subtotal=4000,
        gst_amount=720,
        platform_fee=400,
        total_amount=5120,
        status="hold",
        hold_expires_at=now_utc + datetime.timedelta(minutes=10)
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)

    # Process payment
    updated_b, payment = process_successful_payment(
        db=db_session,
        booking_id=b.id,
        razorpay_order_id="order_test_999",
        razorpay_payment_id="pay_test_999",
        signature="test_signature_valid",
        method="upi"
    )

    assert updated_b.status in ("pending_owner", "confirmed")
    assert payment.status == "captured"
    assert payment.amount == 5120

    # Idempotency test: processing the exact same payment id must not duplicate
    dup_b, dup_p = process_successful_payment(
        db=db_session,
        booking_id=b.id,
        razorpay_order_id="order_test_999",
        razorpay_payment_id="pay_test_999",
        signature="test_signature_valid",
        method="upi"
    )
    assert dup_p.id == payment.id

    # Test PDF invoice generation
    pdf_path = generate_invoice_pdf(updated_b)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000 # Valid non-empty PDF document
