import datetime
from app.models.property import Property
from app.models.booking import Booking
from app.services.refund import calculate_cancellation_refund

def test_flexible_cancellation_policy(test_owner, test_customer):
    prop = Property(
        id=901,
        owner_id=test_owner.id,
        name="Flex Villa",
        city="Chennai",
        area="ECR",
        address="1 ECR Road",
        property_type="villa",
        hourly_price=3000,
        cancellation_policy="flexible"
    )

    now_utc = datetime.datetime.utcnow()

    # 1. > 24 hours out -> 100% rental + GST refund
    b_far = Booking(
        id=901,
        booking_code="#SMS-F1",
        property_id=prop.id,
        customer_id=test_customer.id,
        subtotal=6000,
        gst_amount=1080,
        platform_fee=600,
        total_amount=7680,
        start_datetime=now_utc + datetime.timedelta(hours=48),
        end_datetime=now_utc + datetime.timedelta(hours=50),
        property=prop
    )
    res_far = calculate_cancellation_refund(b_far, cancelled_by="customer")
    assert res_far["refund_percentage"] == 100
    assert res_far["refund_amount"] == 6000 + 1080 # subtotal + GST

    # 2. 6-24 hours out -> 50% rental refund
    b_mid = Booking(
        id=902,
        booking_code="#SMS-F2",
        property_id=prop.id,
        customer_id=test_customer.id,
        subtotal=6000,
        gst_amount=1080,
        platform_fee=600,
        total_amount=7680,
        start_datetime=now_utc + datetime.timedelta(hours=12),
        end_datetime=now_utc + datetime.timedelta(hours=14),
        property=prop
    )
    res_mid = calculate_cancellation_refund(b_mid, cancelled_by="customer")
    assert res_mid["refund_percentage"] == 50
    assert res_mid["refund_amount"] == 3000

    # 3. < 6 hours out -> 0% refund
    b_close = Booking(
        id=903,
        booking_code="#SMS-F3",
        property_id=prop.id,
        customer_id=test_customer.id,
        subtotal=6000,
        gst_amount=1080,
        platform_fee=600,
        total_amount=7680,
        start_datetime=now_utc + datetime.timedelta(hours=3),
        end_datetime=now_utc + datetime.timedelta(hours=5),
        property=prop
    )
    res_close = calculate_cancellation_refund(b_close, cancelled_by="customer")
    assert res_close["refund_percentage"] == 0
    assert res_close["refund_amount"] == 0

def test_owner_cancellation_always_100_percent(test_owner, test_customer):
    prop = Property(
        id=904,
        owner_id=test_owner.id,
        name="Strict Villa",
        city="Chennai",
        area="OMR",
        address="2 OMR Road",
        property_type="villa",
        hourly_price=5000,
        cancellation_policy="strict"
    )

    now_utc = datetime.datetime.utcnow()
    b = Booking(
        id=905,
        booking_code="#SMS-OWN",
        property_id=prop.id,
        customer_id=test_customer.id,
        subtotal=10000,
        gst_amount=1800,
        platform_fee=1000,
        total_amount=12800,
        start_datetime=now_utc + datetime.timedelta(hours=2), # < 7 days would be 0% for customer
        end_datetime=now_utc + datetime.timedelta(hours=4),
        property=prop
    )

    # When owner cancels or rejects: ALWAYS 100% total refund including platform fee
    res_owner = calculate_cancellation_refund(b, cancelled_by="owner")
    assert res_owner["refund_percentage"] == 100
    assert res_owner["refund_amount"] == 12800
    assert res_owner["platform_fee_retained"] == 0
