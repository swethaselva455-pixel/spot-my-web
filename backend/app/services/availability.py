import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.config import settings
from app.models.property import Property, AvailabilityRule, BlockedSlot
from app.models.booking import Booking

IST = ZoneInfo(settings.TIMEZONE) # "Asia/Kolkata"
UTC = ZoneInfo("UTC")

def get_ist_now() -> datetime.datetime:
    return datetime.datetime.now(IST)

def ist_to_utc(dt_ist: datetime.datetime) -> datetime.datetime:
    if dt_ist.tzinfo is None:
        dt_ist = dt_ist.replace(tzinfo=IST)
    return dt_ist.astimezone(UTC).replace(tzinfo=None) # store naive UTC in DB

def utc_to_ist(dt_utc: datetime.datetime) -> datetime.datetime:
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=UTC)
    return dt_utc.astimezone(IST)

def is_slot_available(
    db: Session,
    property_obj: Property,
    start_utc: datetime.datetime,
    end_utc: datetime.datetime,
    exclude_booking_id: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    now_utc = datetime.datetime.utcnow()
    buffer_mins = property_obj.buffer_minutes or settings.DEFAULT_BUFFER_MINUTES
    buffer_delta = datetime.timedelta(minutes=buffer_mins)

    # 1. Past check
    if start_utc <= now_utc:
        return False, "Selected time is in the past."

    # 2. Convert start/end to IST for weekly availability rule check
    start_ist = utc_to_ist(start_utc)
    end_ist = utc_to_ist(end_utc)
    weekday = start_ist.weekday() # 0 = Monday, 6 = Sunday

    rules = [r for r in property_obj.availability_rules if r.day_of_week == weekday]
    if rules:
        # Check if the requested start and end fall completely within open hours
        slot_open = False
        for rule in rules:
            rule_open = datetime.datetime.combine(start_ist.date(), rule.open_time, tzinfo=IST)
            rule_close = datetime.datetime.combine(start_ist.date(), rule.close_time, tzinfo=IST)
            if start_ist >= rule_open and end_ist <= rule_close:
                slot_open = True
                break
        if not slot_open:
            return False, f"Property is not open during these hours on {start_ist.strftime('%A')}."

    # 3. Check blocked slots
    blocked = db.query(BlockedSlot).filter(
        BlockedSlot.property_id == property_obj.id,
        BlockedSlot.start_datetime < end_utc,
        BlockedSlot.end_datetime > start_utc
    ).first()
    if blocked:
        return False, f"Slot is blocked by owner: {blocked.reason}"

    # 4. Check active bookings with buffer time
    # Active statuses: confirmed, pending_owner, or active hold
    buffered_start = start_utc - buffer_delta
    buffered_end = end_utc + buffer_delta

    query = db.query(Booking).filter(
        Booking.property_id == property_obj.id,
        Booking.status.in_(["confirmed", "pending_owner", "hold"]),
        Booking.start_datetime < buffered_end,
        Booking.end_datetime > buffered_start
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)

    conflicts = query.all()
    for conf in conflicts:
        if conf.status == "hold":
            # If hold has expired, it does not block
            if conf.hold_expires_at and conf.hold_expires_at <= now_utc:
                continue
        return False, f"Slot clashes with existing booking ({conf.booking_code}) or cleaning buffer."

    return True, None

def get_day_availability(
    db: Session,
    property_obj: Property,
    date_str: str, # "YYYY-MM-DD"
    slot_interval_minutes: int = 60
) -> List[Dict[str, Any]]:
    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    now_ist = get_ist_now()

    # Determine daily hours (e.g. from availability rules or 06:00 - 22:00)
    weekday = target_date.weekday()
    rules = [r for r in property_obj.availability_rules if r.day_of_week == weekday]

    if rules:
        earliest = min(r.open_time for r in rules)
        latest = max(r.close_time for r in rules)
        day_start = datetime.datetime.combine(target_date, earliest, tzinfo=IST)
        day_end = datetime.datetime.combine(target_date, latest, tzinfo=IST)
    else:
        day_start = datetime.datetime.combine(target_date, datetime.time(6, 0), tzinfo=IST)
        day_end = datetime.datetime.combine(target_date, datetime.time(22, 0), tzinfo=IST)

    slots = []
    curr = day_start
    min_dur = property_obj.min_hours or 2
    step = datetime.timedelta(minutes=slot_interval_minutes)

    while curr < day_end:
        slot_end_single = curr + datetime.timedelta(hours=min_dur)
        if slot_end_single > day_end:
            # Cannot even fit minimum hours from this start time
            slots.append({
                "time": curr.strftime("%H:%M"),
                "display": curr.strftime("%I:%M %p"),
                "available": False,
                "reason": f"Insufficient remaining hours (min {min_dur}h required)"
            })
            curr += step
            continue

        # Check availability for minimum duration
        start_utc = ist_to_utc(curr)
        end_utc = ist_to_utc(slot_end_single)
        avail, reason = is_slot_available(db, property_obj, start_utc, end_utc)

        slots.append({
            "time": curr.strftime("%H:%M"),
            "display": curr.strftime("%I:%M %p"),
            "available": avail,
            "reason": reason if not avail else None
        })
        curr += step

    return slots

def get_month_calendar_summary(
    db: Session,
    property_obj: Property,
    year_month: str # "YYYY-MM"
) -> List[Dict[str, Any]]:
    year, month = map(int, year_month.split("-"))
    # Find number of days in month
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    first_day = datetime.date(year, month, 1)
    days_in_month = (next_month - first_day).days

    today_ist = get_ist_now().date()
    result = []

    for d in range(1, days_in_month + 1):
        day_date = datetime.date(year, month, d)
        date_str = day_date.strftime("%Y-%m-%d")

        if day_date < today_ist:
            result.append({"date": date_str, "status": "past", "available": False})
            continue

        # Check if any slots are available on this date
        slots = get_day_availability(db, property_obj, date_str)
        available_count = sum(1 for s in slots if s["available"])

        if available_count == 0:
            status_str = "booked"
        elif available_count < len(slots) // 2:
            status_str = "limited"
        else:
            status_str = "available"

        result.append({
            "date": date_str,
            "status": status_str,
            "available": available_count > 0,
            "available_slots": available_count
        })

    return result
