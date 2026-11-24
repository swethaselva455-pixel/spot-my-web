import datetime
from app.models.property import Property
from app.models.booking import Booking
from app.models.notification import Notification
from app.scheduler.jobs import run_scheduler_jobs
from app.services.notification import send_notification

def test_hold_expiration_and_notifications(db_session, test_owner, test_customer):
    prop = Property(
        owner_id=test_owner.id,
        name="Reminder Test Villa",
        city="Chennai",
        area="ECR",
        address="55 Beach Road",
        property_type="villa",
        hourly_price=3000,
        approval_status="approved",
        is_published=True
    )
    db_session.add(prop)
    db_session.commit()

    now_utc = datetime.datetime.utcnow()

    # Create an expired hold (hold_expires_at was 5 minutes ago)
    expired_booking = Booking(
        booking_code="#SMS-EXP1",
        property_id=prop.id,
        customer_id=test_customer.id,
        shoot_category="Reels",
        start_datetime=now_utc + datetime.timedelta(days=2),
        end_datetime=now_utc + datetime.timedelta(days=2, hours=2),
        duration_hours=2,
        crew_size=4,
        subtotal=6000,
        gst_amount=1080,
        platform_fee=600,
        total_amount=7680,
        status="hold",
        hold_expires_at=now_utc - datetime.timedelta(minutes=5)
    )
    db_session.add(expired_booking)
    db_session.commit()

    # Run scheduler job
    run_scheduler_jobs(db=db_session)

    db_session.refresh(expired_booking)
    assert expired_booking.status == "expired"

    # Notification idempotency test
    # Sending reminder twice for same booking & user must not duplicate
    n1 = send_notification(
        db=db_session,
        user_id=test_customer.id,
        type_name="reminder_24h",
        title="Shoot Tomorrow",
        message="Your shoot is scheduled tomorrow.",
        booking_id=expired_booking.id,
        channel="in_app"
    )
    n2 = send_notification(
        db=db_session,
        user_id=test_customer.id,
        type_name="reminder_24h",
        title="Shoot Tomorrow",
        message="Your shoot is scheduled tomorrow.",
        booking_id=expired_booking.id,
        channel="in_app"
    )
    assert n1.id == n2.id
