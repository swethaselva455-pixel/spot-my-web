import random
import datetime
import threading
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.config import settings
from app.models.property import Property
from app.models.booking import Booking
from app.services.availability import (
    ist_to_utc, utc_to_ist, is_slot_available, IST
)

_property_locks: Dict[int, threading.Lock] = {}
_global_booking_lock = threading.Lock()

def get_property_lock(property_id: int) -> threading.Lock:
    with _global_booking_lock:
        if property_id not in _property_locks:
            _property_locks[property_id] = threading.Lock()
        return _property_locks[property_id]

def generate_booking_code(db: Session) -> str:
    for _ in range(10):
        code_num = random.randint(1000, 9999)
        code = f"#SMS-{code_num}"
        exists = db.query(Booking).filter(Booking.booking_code == code).first()
        if not exists:
            return code
    return f"#SMS-{int(datetime.datetime.utcnow().timestamp())}"

def calculate_quote(property_obj: Property, duration_hours: int) -> Dict[str, Any]:
    if duration_hours < property_obj.min_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Duration must be at least {property_obj.min_hours} hours for this property."
        )
    if duration_hours > property_obj.max_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Duration cannot exceed {property_obj.max_hours} hours for this property."
        )

    subtotal = property_obj.hourly_price * duration_hours
    gst_percent = float(settings.GST_PERCENT)
    gst_amount = int(round(subtotal * (gst_percent / 100.0)))
    platform_fee = int(round(subtotal * (float(settings.PLATFORM_COMMISSION_PERCENT) / 100.0)))
    total_amount = subtotal + gst_amount + platform_fee

    return {
        "property_id": property_obj.id,
        "property_name": property_obj.name,
        "hourly_price": property_obj.hourly_price,
        "duration_hours": duration_hours,
        "subtotal": subtotal,
        "gst_percent": gst_percent,
        "gst_amount": gst_amount,
        "platform_fee": platform_fee,
        "total_amount": total_amount,
        "cancellation_policy": property_obj.cancellation_policy
    }

def create_booking_hold(
    db: Session,
    customer_id: int,
    property_id: int,
    shoot_category: str,
    date_str: str,
    start_time_str: str,
    duration_hours: int,
    crew_size: int,
    special_requests: str = None
) -> Booking:
    with get_property_lock(property_id):
        # 1. Fetch property with lock if supported (SELECT FOR UPDATE)
        try:
            property_obj = db.query(Property).filter(Property.id == property_id).with_for_update().first()
        except Exception:
            property_obj = db.query(Property).filter(Property.id == property_id).first()

        if not property_obj:
            raise HTTPException(status_code=404, detail="Property not found.")

        if not property_obj.is_published or property_obj.approval_status != "approved":
            raise HTTPException(status_code=400, detail="This property is not currently active for bookings.")

        if crew_size > property_obj.max_crew_size:
            raise HTTPException(
                status_code=400,
                detail=f"Crew size ({crew_size}) exceeds maximum allowed ({property_obj.max_crew_size}) for this property."
            )

        # 2. Parse timestamps (User provides date & time in IST)
        start_time_parts = list(map(int, start_time_str.split(":")))
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        start_ist = datetime.datetime(
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            hour=start_time_parts[0],
            minute=start_time_parts[1],
            tzinfo=IST
        )
        end_ist = start_ist + datetime.timedelta(hours=duration_hours)

        start_utc = ist_to_utc(start_ist)
        end_utc = ist_to_utc(end_ist)

        # 3. Check availability strictly
        available, reason = is_slot_available(db, property_obj, start_utc, end_utc)
        if not available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slot is no longer available: {reason}"
            )

        # 4. Calculate pricing
        quote = calculate_quote(property_obj, duration_hours)

        # 5. Create booking with status 'hold'
        now_utc = datetime.datetime.utcnow()
        hold_expiry = now_utc + datetime.timedelta(minutes=settings.BOOKING_HOLD_MINUTES)
        booking_code = generate_booking_code(db)

        booking = Booking(
            booking_code=booking_code,
            property_id=property_obj.id,
            customer_id=customer_id,
            shoot_category=shoot_category,
            start_datetime=start_utc,
            end_datetime=end_utc,
            duration_hours=duration_hours,
            crew_size=crew_size,
            special_requests=special_requests,
            subtotal=quote["subtotal"],
            gst_amount=quote["gst_amount"],
            platform_fee=quote["platform_fee"],
            total_amount=quote["total_amount"],
            status="hold",
            hold_expires_at=hold_expiry
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking
