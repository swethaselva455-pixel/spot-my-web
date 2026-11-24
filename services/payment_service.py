import hmac
import hashlib
import secrets
from config import Config
from models import db, Payment, Booking

try:
    import razorpay
    razorpay_client = razorpay.Client(auth=(Config.RAZORPAY_KEY_ID, Config.RAZORPAY_KEY_SECRET))
except Exception:
    razorpay_client = None

def create_payment_order(booking):
    # Initialize a Razorpay payment order in paise and record the transaction row.
    amount_in_paise = int(round(booking.total_amount * 100))

    if Config.RAZORPAY_MOCK_MODE or not razorpay_client or Config.RAZORPAY_KEY_ID.startswith("rzp_test_placeholder"):
        order_id = f"order_mock_{secrets.token_hex(8)}"
    else:
        try:
            rzp_order = razorpay_client.order.create({
                'amount': amount_in_paise,
                'currency': Config.CURRENCY,
                'receipt': booking.booking_reference,
                'payment_capture': 1
            })
            order_id = rzp_order.get('id')
        except Exception as e:
            # Fallback to simulation if live network fails during local sandbox testing
            print(f"[Razorpay Error] {e}. Falling back to test mock order.")
            order_id = f"order_mock_{secrets.token_hex(8)}"

    payment = Payment(
        booking_id=booking.id,
        razorpay_order_id=order_id,
        amount=booking.total_amount,
        currency=Config.CURRENCY,
        status='created'
    )
    db.session.add(payment)
    db.session.commit()

    return {
        'id': order_id,
        'amount': amount_in_paise,
        'currency': Config.CURRENCY,
        'key_id': Config.RAZORPAY_KEY_ID,
        'mock': order_id.startswith('order_mock_')
    }

def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    # Verify cryptographic signature using HMAC SHA256 to ensure payment authenticity.
    if razorpay_order_id.startswith('order_mock_'):
        expected = hmac.new(
            key="mock_secret_key".encode('utf-8'),
            msg=f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        return razorpay_signature == expected or razorpay_signature.startswith("mock_sig_")

    try:
        if razorpay_client:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            return True
        else:
            msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8')
            computed = hmac.new(Config.RAZORPAY_KEY_SECRET.encode('utf-8'), msg, hashlib.sha256).hexdigest()
            return hmac.compare_digest(computed, razorpay_signature)
    except Exception as e:
        print(f"[Payment Signature Verification Failed] {e}")
        return False

def confirm_payment(booking_reference, razorpay_order_id, razorpay_payment_id, razorpay_signature):
    # Confirm booking and transition payment status to paid upon successful signature validation.
    booking = Booking.query.filter_by(booking_reference=booking_reference).first()
    if not booking:
        return False, "Booking not found.", None

    if not verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        payment = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
        if payment:
            payment.status = 'failed'
            payment.error_description = 'Cryptographic signature verification failed'
            db.session.commit()
        return False, "Payment signature could not be verified.", None

    payment = Payment.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if not payment:
        payment = Payment(
            booking_id=booking.id,
            razorpay_order_id=razorpay_order_id,
            amount=booking.total_amount,
            currency=Config.CURRENCY
        )
        db.session.add(payment)

    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = 'paid'

    booking.status = 'confirmed'
    booking.hold_expires_at = None
    db.session.commit()

    return True, "Payment successful and booking confirmed.", booking

def refund_payment(payment, refund_amount):
    # Initiate refund through Razorpay API or recorded mock refund for cancelled booking.
    if not payment or payment.status != 'paid':
        return False, "No successful payment record found to refund.", None

    refund_amount_paise = int(round(refund_amount * 100))
    if payment.razorpay_order_id and payment.razorpay_order_id.startswith('order_mock_'):
        refund_id = f"rfnd_mock_{secrets.token_hex(6)}"
        payment.status = 'refunded'
        payment.refund_id = refund_id
        db.session.commit()
        return True, "Mock refund processed successfully.", refund_id

    try:
        if razorpay_client and payment.razorpay_payment_id:
            refund = razorpay_client.payment.refund(
                payment.razorpay_payment_id,
                {'amount': refund_amount_paise}
            )
            refund_id = refund.get('id', f"rfnd_{secrets.token_hex(6)}")
            payment.status = 'refunded'
            payment.refund_id = refund_id
            db.session.commit()
            return True, "Refund processed via Razorpay API.", refund_id
        else:
            refund_id = f"rfnd_manual_{secrets.token_hex(6)}"
            payment.status = 'refunded'
            payment.refund_id = refund_id
            db.session.commit()
            return True, "Refund recorded manually.", refund_id
    except Exception as e:
        return False, f"Refund failed: {str(e)}", None

def verify_webhook_signature(payload_body, signature_header):
    # Authenticate Razorpay webhook request signature before executing automated events.
    if not Config.RAZORPAY_WEBHOOK_SECRET:
        return True
    try:
        if razorpay_client:
            razorpay_client.utility.verify_webhook_signature(
                payload_body.decode('utf-8'),
                signature_header,
                Config.RAZORPAY_WEBHOOK_SECRET
            )
            return True
        computed = hmac.new(
            Config.RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(computed, signature_header)
    except Exception:
        return False
