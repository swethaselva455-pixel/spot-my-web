import datetime
import concurrent.futures
from fastapi import HTTPException
from app.models.property import Property, AvailabilityRule
from app.models.booking import Booking
from app.services.booking import create_booking_hold
from tests.conftest import TestingSessionLocal

def test_concurrent_double_booking_prevention(db_session, test_owner, test_customer):
    # Setup test property
    prop = Property(
        owner_id=test_owner.id,
        name="Parallel Test Studio",
        city="Chennai",
        area="Adyar",
        address="12 Central Road",
        property_type="studio",
        hourly_price=2000,
        min_hours=2,
        max_hours=6,
        max_crew_size=15,
        approval_status="approved",
        is_published=True
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)

    for day in range(7):
        db_session.add(AvailabilityRule(
            property_id=prop.id,
            day_of_week=day,
            open_time=datetime.time(6, 0),
            close_time=datetime.time(22, 0)
        ))
    db_session.commit()

    target_date = (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    results = []

    def make_booking_attempt(attempt_id):
        local_db = TestingSessionLocal()
        try:
            booking = create_booking_hold(
                db=local_db,
                customer_id=test_customer.id,
                property_id=prop.id,
                shoot_category="Fashion",
                date_str=target_date,
                start_time_str="10:00",
                duration_hours=3,
                crew_size=5
            )
            return 201, booking.booking_code
        except HTTPException as e:
            return e.status_code, e.detail
        except Exception as ex:
            return 500, str(ex)
        finally:
            local_db.close()

    # Fire 5 concurrent threads attempting to book the EXACT same slot
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_booking_attempt, i) for i in range(5)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    status_codes = [r[0] for r in results]

    # Exactly 1 attempt must succeed (201), the other 4 must be rejected with 409 Conflict
    success_count = status_codes.count(201)
    conflict_count = status_codes.count(409)

    assert success_count == 1, f"Expected 1 success, got {success_count}. Results: {results}"
    assert conflict_count == 4, f"Expected 4 conflicts, got {conflict_count}. Results: {results}"

    # Verify only 1 booking exists in DB
    db_bookings = db_session.query(Booking).filter(
        Booking.property_id == prop.id,
        Booking.status == "hold"
    ).all()
    assert len(db_bookings) == 1
