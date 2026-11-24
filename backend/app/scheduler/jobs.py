import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models.booking import Booking
from app.models.notification import Notification
from app.services.refund import calculate_cancellation_refund, execute_booking_refund
from app.services.notification import send_notification
from app.services.availability import utc_to_ist, IST

from typing import Optional

scheduler = BackgroundScheduler()

def run_scheduler_jobs(db: Optional[Session] = None):
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    try:
        now_utc = datetime.datetime.utcnow()

        # -------------------------------------------------------------
        # 1. Release Expired Booking Holds & send 2-min warning
        # -------------------------------------------------------------
        active_holds = db.query(Booking).filter(Booking.status == "hold").all()
        for hold in active_holds:
            if hold.hold_expires_at:
                seconds_left = (hold.hold_expires_at - now_utc).total_seconds()
                if seconds_left <= 0:
                    hold.status = "expired"
                    db.commit()
                    send_notification(
                        db=db,
                        user_id=hold.customer_id,
                        type_name="hold_expired",
                        title=f"Hold Expired for {hold.booking_code}",
                        message="Your 10-minute booking hold has expired. The time slot has been released back to other creators.",
                        booking_id=hold.id,
                        channel="in_app"
                    )
                elif 0 < seconds_left <= 120:
                    # 2-minute expiring warning
                    send_notification(
                        db=db,
                        user_id=hold.customer_id,
                        type_name="reminder_hold_expiring",
                        title="Booking Hold Expiring in 2 Minutes!",
                        message=f"Only 2 minutes remain on your reservation hold for {hold.booking_code}. Complete payment now to secure the location.",
                        booking_id=hold.id,
                        channel="in_app"
                    )

        # -------------------------------------------------------------
        # 2. Check Pending Owner Response Timeout (12h) & 6h nudge
        # -------------------------------------------------------------
        timeout_threshold = now_utc - datetime.timedelta(hours=settings.OWNER_RESPONSE_TIMEOUT_HOURS)
        nudge_threshold = now_utc - datetime.timedelta(hours=6)

        pending_bookings = db.query(Booking).filter(Booking.status == "pending_owner").all()
        for b in pending_bookings:
            if b.created_at <= timeout_threshold:
                # Auto-cancel and trigger full automatic refund
                execute_booking_refund(
                    db=db,
                    booking=b,
                    refund_amount=b.total_amount,
                    reason=f"Owner did not respond within {settings.OWNER_RESPONSE_TIMEOUT_HOURS} hours. Automatic full refund processed.",
                    cancelled_by="timeout",
                    actor_id=b.customer_id
                )
            elif b.created_at <= nudge_threshold:
                # 6-hour nudge to owner
                if b.property and b.property.owner_id:
                    send_notification(
                        db=db,
                        user_id=b.property.owner_id,
                        type_name="reminder_owner_nudge_6h",
                        title="Reminder: Respond to Booking Request",
                        message=f"You have a pending booking request ({b.booking_code}) waiting for approval. Please accept or decline to avoid automatic refund.",
                        booking_id=b.id,
                        channel="in_app"
                    )

        # -------------------------------------------------------------
        # 3. Upcoming Shoot Reminders (24 hours and 2 hours before start)
        # -------------------------------------------------------------
        confirmed_shoots = db.query(Booking).filter(Booking.status == "confirmed").all()
        for b in confirmed_shoots:
            hours_until_start = (b.start_datetime - now_utc).total_seconds() / 3600.0

            # 24 Hours Reminder (between 23 and 25 hours out)
            if 23.0 <= hours_until_start <= 25.0:
                start_ist = utc_to_ist(b.start_datetime)
                msg_cust = (
                    f"Reminder: Your shoot at {b.property.name} is tomorrow, {start_ist.strftime('%d %b at %I:%M %p')}. "
                    f"Address: {b.property.address}. Crew size limit: {b.crew_size}. Please bring your photo ID."
                )
                send_notification(
                    db=db,
                    user_id=b.customer_id,
                    type_name="reminder_24h",
                    title="Shoot Tomorrow: SpotMyShoot Reminder",
                    message=msg_cust,
                    booking_id=b.id,
                    channel="in_app"
                )
                if b.property and b.property.owner_id:
                    send_notification(
                        db=db,
                        user_id=b.property.owner_id,
                        type_name="reminder_owner_24h",
                        title="Upcoming Shoot Tomorrow",
                        message=f"Reminder: You have a shoot scheduled tomorrow at {b.property.name} ({b.booking_code}) starting at {start_ist.strftime('%I:%M %p')}.",
                        booking_id=b.id,
                        channel="in_app"
                    )

            # 2 Hours Reminder (between 1.5 and 2.5 hours out)
            if 1.5 <= hours_until_start <= 2.5:
                start_ist = utc_to_ist(b.start_datetime)
                owner_phone = b.property.owner.phone if (b.property and b.property.owner and b.property.owner.phone) else "Contact via app"
                map_url = f"https://www.google.com/maps/search/?api=1&query={b.property.latitude},{b.property.longitude}" if (b.property and b.property.latitude) else ""
                msg_cust = (
                    f"Shoot Starting in 2 Hours! Location: {b.property.name}, {b.property.address}. "
                    f"Owner Contact: {owner_phone}. Map: {map_url}. Crew checklist: gear charged, talent briefed."
                )
                send_notification(
                    db=db,
                    user_id=b.customer_id,
                    type_name="reminder_2h",
                    title="Shoot Starting in 2 Hours!",
                    message=msg_cust,
                    booking_id=b.id,
                    channel="in_app"
                )

            # ---------------------------------------------------------
            # 4. Mark Shoot Completed after End Time
            # ---------------------------------------------------------
            if now_utc >= b.end_datetime:
                b.status = "completed"
                db.commit()

        # -------------------------------------------------------------
        # 5. Post-Shoot Review Request (3 hours after end time)
        # -------------------------------------------------------------
        completed_shoots = db.query(Booking).filter(Booking.status == "completed").all()
        for b in completed_shoots:
            hours_since_end = (now_utc - b.end_datetime).total_seconds() / 3600.0
            if hours_since_end >= 3.0:
                # Check if review already submitted
                if not b.review:
                    send_notification(
                        db=db,
                        user_id=b.customer_id,
                        type_name="reminder_review_request",
                        title="How was your shoot? Rate your experience!",
                        message=f"We hope your shoot at {b.property.name} went great! Leave a quick review to help other creators in the community.",
                        booking_id=b.id,
                        channel="in_app"
                    )

    except Exception as e:
        print(f"[SCHEDULER ERROR] {e}")
    finally:
        if should_close:
            db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(run_scheduler_jobs, "interval", minutes=1, id="spotmyshoot_lifecycle_job", replace_existing=True)
        scheduler.start()
        print("[SCHEDULER] APScheduler started successfully.")
