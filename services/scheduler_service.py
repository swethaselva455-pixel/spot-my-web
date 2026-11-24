from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, Booking, Slot
from services.availability import release_expired_holds
from services.notification_service import send_reminder_email

scheduler = BackgroundScheduler()

def run_hold_cleanup_job(app):
    # Scheduled background job to release expired 10-minute checkout holds.
    with app.app_context():
        count = release_expired_holds()
        if count > 0:
            print(f"[Scheduler] Released {count} expired checkout holds.")

def run_reminder_notifications_job(app):
    # Scheduled job to scan upcoming confirmed bookings and trigger 24-hour and 1-hour reminder emails.
    with app.app_context():
        now_utc = datetime.now(timezone.utc)
        confirmed_bookings = Booking.query.filter_by(status='confirmed').all()

        for b in confirmed_bookings:
            if not b.slot:
                continue

            try:
                start_t = datetime.strptime(b.slot.start_time, "%H:%M").time()
            except Exception:
                start_t = datetime.strptime("09:00", "%H:%M").time()

            appointment_dt = datetime.combine(b.slot.slot_date, start_t).replace(tzinfo=timezone.utc)
            seconds_remaining = (appointment_dt - now_utc).total_seconds()
            hours_remaining = seconds_remaining / 3600.0

            # 24-hour reminder window: between 23h and 25h before appointment
            if not b.reminder_24h_sent and 23.0 <= hours_remaining <= 25.0:
                sent = send_reminder_email(b, "24 hours")
                if sent:
                    b.reminder_24h_sent = True
                    db.session.commit()
                    print(f"[Scheduler] 24h reminder delivered for {b.booking_reference}")

            # 1-hour reminder window: between 45m and 75m before appointment
            elif not b.reminder_1h_sent and 0.75 <= hours_remaining <= 1.25:
                sent = send_reminder_email(b, "1 hour")
                if sent:
                    b.reminder_1h_sent = True
                    db.session.commit()
                    print(f"[Scheduler] 1h reminder delivered for {b.booking_reference}")

def init_scheduler(app):
    # Register periodic interval jobs and start background APScheduler thread.
    if not scheduler.running:
        scheduler.add_job(
            func=run_hold_cleanup_job,
            args=[app],
            trigger="interval",
            seconds=60,
            id="cleanup_holds_job",
            replace_existing=True
        )
        scheduler.add_job(
            func=run_reminder_notifications_job,
            args=[app],
            trigger="interval",
            seconds=60,
            id="reminder_dispatch_job",
            replace_existing=True
        )
        scheduler.start()
        print("[Scheduler] APScheduler background engine started successfully.")
    return scheduler
