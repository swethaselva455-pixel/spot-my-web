from datetime import datetime, date, timedelta, timezone
from models import db, Slot, Booking

def release_expired_holds():
    # Mark expired pending checkout bookings so held slots are immediately released.
    now_utc = datetime.now(timezone.utc)
    expired_bookings = Booking.query.filter(
        Booking.status == 'pending',
        Booking.hold_expires_at.isnot(None),
        Booking.hold_expires_at < now_utc
    ).all()

    for booking in expired_bookings:
        booking.status = 'cancelled'
        booking.cancellation_reason = 'Checkout hold timer expired'
    if expired_bookings:
        db.session.commit()
    return len(expired_bookings)

def get_slots_for_date(service_id, target_date):
    # Fetch all slots for a given service and date, calculating live availability.
    release_expired_holds()
    slots = Slot.query.filter_by(service_id=service_id, slot_date=target_date).order_by(Slot.start_time).all()
    slot_list = []
    for s in slots:
        available = s.is_available()
        slot_list.append({
            'id': s.id,
            'service_id': s.service_id,
            'slot_date': s.slot_date.strftime('%Y-%m-%d'),
            'start_time': s.start_time,
            'end_time': s.end_time,
            'capacity': s.capacity,
            'is_blocked': s.is_blocked,
            'is_available': available,
            'booked_count': s.active_reservations_count()
        })
    return slot_list

def is_slot_available_for_booking(slot_id):
    # Double-check availability directly from database state before initiating hold.
    release_expired_holds()
    slot = db.session.get(Slot, slot_id)
    if not slot or slot.is_blocked:
        return False, "Selected slot is unavailable or blocked."
    if not slot.is_available():
        return False, "This slot was just taken. Please select another time."
    return True, "Slot is available."

def generate_slots(service_id, start_date, end_date, time_slots, capacity=1):
    # Generate bulk date slots with custom timings and capacity for a service.
    created_count = 0
    delta = (end_date - start_date).days + 1
    for day in range(delta):
        curr_date = start_date + timedelta(days=day)
        for start_t, end_t in time_slots:
            existing = Slot.query.filter_by(
                service_id=service_id,
                slot_date=curr_date,
                start_time=start_t
            ).first()
            if not existing:
                new_slot = Slot(
                    service_id=service_id,
                    slot_date=curr_date,
                    start_time=start_t,
                    end_time=end_t,
                    capacity=capacity,
                    is_blocked=False
                )
                db.session.add(new_slot)
                created_count += 1
    db.session.commit()
    return created_count

def toggle_slot_block(slot_id):
    # Toggle the blocked status of an individual slot.
    slot = db.session.get(Slot, slot_id)
    if not slot:
        return None
    slot.is_blocked = not slot.is_blocked
    db.session.commit()
    return slot.is_blocked
