import datetime
import pytest
from app.models.property import Property, AvailabilityRule, BlockedSlot
from app.models.booking import Booking
from app.services.availability import (
    is_slot_available, get_day_availability, ist_to_utc, IST
)

def test_availability_and_buffer(db_session, test_owner):
    prop = Property(
        owner_id=test_owner.id,
        name="Sunset Garden Villa",
        city="Chennai",
        area="ECR",
        address="10 Beach Road",
        property_type="villa",
        hourly_price=3000,
        min_hours=2,
        max_hours=8,
        max_crew_size=20,
        cancellation_policy="flexible",
        approval_status="approved",
        is_published=True,
        buffer_minutes=30
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    # Add open hours: Monday-Sunday 06:00 to 20:00
    for day in range(7):
        db_session.add(AvailabilityRule(
            property_id=prop.id,
            day_of_week=day,
            open_time=datetime.time(6, 0),
            close_time=datetime.time(20, 0)
        ))
    db_session.commit()

    # 1. Test future valid slot
    target_date = datetime.date.today() + datetime.timedelta(days=10)
    slot1_start_ist = datetime.datetime.combine(target_date, datetime.time(10, 0), tzinfo=IST)
    slot1_end_ist = slot1_start_ist + datetime.timedelta(hours=3)

    slot1_start_utc = ist_to_utc(slot1_start_ist)
    slot1_end_utc = ist_to_utc(slot1_end_ist)

    avail, reason = is_slot_available(db_session, prop, slot1_start_utc, slot1_end_utc)
    assert avail is True
    assert reason is None

    # 2. Test past slot is blocked
    past_start = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    past_end = past_start + datetime.timedelta(hours=2)
    avail_past, reason_past = is_slot_available(db_session, prop, past_start, past_end)
    assert avail_past is False
    assert "past" in reason_past.lower()

    # 3. Test booking overlap with buffer time
    # Create booking from 10:00 to 13:00
    booking = Booking(
        booking_code="#SMS-TEST1",
        property_id=prop.id,
        customer_id=test_owner.id,
        shoot_category="Pre-wedding",
        start_datetime=slot1_start_utc,
        end_datetime=slot1_end_utc,
        duration_hours=3,
        subtotal=9000,
        gst_amount=1620,
        platform_fee=900,
        total_amount=11520,
        status="confirmed"
    )
    db_session.add(booking)
    db_session.commit()

    # Now attempt booking immediately adjacent at 13:15 (inside 30-min buffer)
    clash_start_ist = datetime.datetime.combine(target_date, datetime.time(13, 15), tzinfo=IST)
    clash_end_ist = clash_start_ist + datetime.timedelta(hours=2)
    avail_buffer, reason_buffer = is_slot_available(db_session, prop, ist_to_utc(clash_start_ist), ist_to_utc(clash_end_ist))
    assert avail_buffer is False
    assert "buffer" in reason_buffer.lower() or "clashes" in reason_buffer.lower()

    # 4. Attempt booking after buffer (e.g. at 14:00)
    clear_start_ist = datetime.datetime.combine(target_date, datetime.time(14, 0), tzinfo=IST)
    clear_end_ist = clear_start_ist + datetime.timedelta(hours=2)
    avail_clear, _ = is_slot_available(db_session, prop, ist_to_utc(clear_start_ist), ist_to_utc(clear_end_ist))
    assert avail_clear is True

    # 5. Test owner blocked slot
    block_start_ist = datetime.datetime.combine(target_date, datetime.time(16, 0), tzinfo=IST)
    block_end_ist = datetime.datetime.combine(target_date, datetime.time(18, 0), tzinfo=IST)
    db_session.add(BlockedSlot(
        property_id=prop.id,
        start_datetime=ist_to_utc(block_start_ist),
        end_datetime=ist_to_utc(block_end_ist),
        reason="Pool Maintenance"
    ))
    db_session.commit()

    avail_blocked, reason_blocked = is_slot_available(db_session, prop, ist_to_utc(block_start_ist), ist_to_utc(block_end_ist))
    assert avail_blocked is False
    assert "blocked by owner" in reason_blocked.lower()
