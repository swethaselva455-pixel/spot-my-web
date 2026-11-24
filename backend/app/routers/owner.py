import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.user import User
from app.models.property import Property, PropertyImage, PropertyCategory, AvailabilityRule, BlockedSlot
from app.models.booking import Booking
from app.schemas.property import (
    PropertyCreateUpdate, PropertyDetailOut, PropertyListItem,
    AvailabilityRuleBase, AvailabilityRuleOut, BlockedSlotBase, BlockedSlotOut
)
from app.schemas.booking import BookingOut
from app.schemas.admin import ReasonRequest
from app.utils.dependencies import get_current_user, require_role, require_approved_user
from app.services.storage import save_upload_file
from app.services.refund import execute_booking_refund
from app.services.notification import send_notification
from app.routers.bookings import map_booking_to_out
from app.services.availability import ist_to_utc, IST

router = APIRouter(prefix="/owner", tags=["Owner"])

@router.get("/properties", response_model=List[PropertyDetailOut])
def get_my_properties(
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    props = db.query(Property).filter(Property.owner_id == current_user.id).order_by(desc(Property.id)).all()
    out = []
    for p in props:
        cats = [c.category for c in p.categories]
        out.append(
            PropertyDetailOut(
                id=p.id,
                owner_id=p.owner_id,
                owner_name=current_user.name,
                name=p.name,
                description=p.description,
                city=p.city,
                area=p.area,
                address=p.address,
                latitude=p.latitude,
                longitude=p.longitude,
                property_type=p.property_type,
                hourly_price=p.hourly_price,
                min_hours=p.min_hours,
                max_hours=p.max_hours,
                max_crew_size=p.max_crew_size,
                amenities=p.amenities or [],
                rules_text=p.rules_text,
                cancellation_policy=p.cancellation_policy,
                approval_status=p.approval_status,
                is_published=p.is_published,
                auto_accept=p.auto_accept,
                avg_rating=p.avg_rating,
                buffer_minutes=p.buffer_minutes,
                created_at=p.created_at,
                images=p.images,
                categories=cats,
                availability_rules=p.availability_rules
            )
        )
    return out

@router.post("/properties", response_model=PropertyDetailOut, status_code=status.HTTP_201_CREATED)
def create_property(
    body: PropertyCreateUpdate,
    current_user: User = Depends(require_approved_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners can list properties.")

    p = Property(
        owner_id=current_user.id,
        name=body.name,
        description=body.description,
        city=body.city,
        area=body.area,
        address=body.address,
        latitude=body.latitude,
        longitude=body.longitude,
        property_type=body.property_type,
        hourly_price=body.hourly_price,
        min_hours=body.min_hours,
        max_hours=body.max_hours,
        max_crew_size=body.max_crew_size,
        amenities=body.amenities,
        rules_text=body.rules_text,
        cancellation_policy=body.cancellation_policy,
        approval_status="pending", # awaits admin approval
        is_published=False,
        auto_accept=body.auto_accept,
        buffer_minutes=body.buffer_minutes
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    # Categories
    for cat in body.categories:
        db.add(PropertyCategory(property_id=p.id, category=cat))

    # Default availability rules (e.g. 06:00 to 22:00 for all 7 days)
    for day in range(7):
        db.add(AvailabilityRule(
            property_id=p.id,
            day_of_week=day,
            open_time=datetime.time(6, 0),
            close_time=datetime.time(22, 0)
        ))

    db.commit()
    db.refresh(p)
    cats = [c.category for c in p.categories]
    return PropertyDetailOut(
        id=p.id,
        owner_id=p.owner_id,
        owner_name=current_user.name,
        name=p.name,
        description=p.description,
        city=p.city,
        area=p.area,
        address=p.address,
        latitude=p.latitude,
        longitude=p.longitude,
        property_type=p.property_type,
        hourly_price=p.hourly_price,
        min_hours=p.min_hours,
        max_hours=p.max_hours,
        max_crew_size=p.max_crew_size,
        amenities=p.amenities or [],
        rules_text=p.rules_text,
        cancellation_policy=p.cancellation_policy,
        approval_status=p.approval_status,
        is_published=p.is_published,
        auto_accept=p.auto_accept,
        avg_rating=p.avg_rating,
        buffer_minutes=p.buffer_minutes,
        created_at=p.created_at,
        images=[],
        categories=cats,
        availability_rules=p.availability_rules
    )

@router.put("/properties/{id}", response_model=PropertyDetailOut)
def update_property(
    id: int,
    body: PropertyCreateUpdate,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")

    if p.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    p.name = body.name
    p.description = body.description
    p.city = body.city
    p.area = body.area
    p.address = body.address
    p.latitude = body.latitude
    p.longitude = body.longitude
    p.property_type = body.property_type
    p.hourly_price = body.hourly_price
    p.min_hours = body.min_hours
    p.max_hours = body.max_hours
    p.max_crew_size = body.max_crew_size
    p.amenities = body.amenities
    p.rules_text = body.rules_text
    p.cancellation_policy = body.cancellation_policy
    p.auto_accept = body.auto_accept
    p.buffer_minutes = body.buffer_minutes

    # Update categories
    db.query(PropertyCategory).filter(PropertyCategory.property_id == p.id).delete()
    for cat in body.categories:
        db.add(PropertyCategory(property_id=p.id, category=cat))

    db.commit()
    db.refresh(p)
    cats = [c.category for c in p.categories]
    return PropertyDetailOut(
        id=p.id,
        owner_id=p.owner_id,
        owner_name=current_user.name,
        name=p.name,
        description=p.description,
        city=p.city,
        area=p.area,
        address=p.address,
        latitude=p.latitude,
        longitude=p.longitude,
        property_type=p.property_type,
        hourly_price=p.hourly_price,
        min_hours=p.min_hours,
        max_hours=p.max_hours,
        max_crew_size=p.max_crew_size,
        amenities=p.amenities or [],
        rules_text=p.rules_text,
        cancellation_policy=p.cancellation_policy,
        approval_status=p.approval_status,
        is_published=p.is_published,
        auto_accept=p.auto_accept,
        avg_rating=p.avg_rating,
        buffer_minutes=p.buffer_minutes,
        created_at=p.created_at,
        images=p.images,
        categories=cats,
        availability_rules=p.availability_rules
    )

@router.delete("/properties/{id}")
def delete_property(
    id: int,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")
    if p.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    db.delete(p)
    db.commit()
    return {"message": "Property deleted successfully."}

@router.post("/properties/{id}/images")
async def upload_property_image(
    id: int,
    file: UploadFile = File(...),
    is_cover: bool = Form(False),
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")
    if p.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    file_url = await save_upload_file(file)

    if is_cover:
        # unset previous cover
        for img in p.images:
            img.is_cover = False

    img_record = PropertyImage(
        property_id=p.id,
        url=file_url,
        is_cover=is_cover or (len(p.images) == 0),
        sort_order=len(p.images)
    )
    db.add(img_record)
    db.commit()
    db.refresh(img_record)

    return {"id": img_record.id, "url": img_record.url, "is_cover": img_record.is_cover}

@router.get("/properties/{id}/availability", response_model=List[AvailabilityRuleOut])
def get_property_rules(
    id: int,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")
    if p.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    rules = db.query(AvailabilityRule).filter(AvailabilityRule.property_id == id).order_by(AvailabilityRule.day_of_week).all()
    return [
        AvailabilityRuleOut(
            id=r.id,
            day_of_week=r.day_of_week,
            open_time=r.open_time.strftime("%H:%M"),
            close_time=r.close_time.strftime("%H:%M")
        )
        for r in rules
    ]

@router.put("/properties/{id}/availability")
def set_property_rules(
    id: int,
    rules: List[AvailabilityRuleBase],
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")
    if p.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    db.query(AvailabilityRule).filter(AvailabilityRule.property_id == id).delete()
    for r in rules:
        ot = datetime.datetime.strptime(r.open_time, "%H:%M").time()
        ct = datetime.datetime.strptime(r.close_time, "%H:%M").time()
        db.add(AvailabilityRule(
            property_id=id,
            day_of_week=r.day_of_week,
            open_time=ot,
            close_time=ct
        ))
    db.commit()
    return {"message": "Availability rules updated successfully."}

@router.post("/properties/{id}/block-slot")
def block_slot(
    id: int,
    body: BlockedSlotBase,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")
    if p.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    start_utc = ist_to_utc(body.start_datetime)
    end_utc = ist_to_utc(body.end_datetime)

    slot = BlockedSlot(
        property_id=id,
        start_datetime=start_utc,
        end_datetime=end_utc,
        reason=body.reason or "Owner Block"
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return {"id": slot.id, "message": "Slot blocked successfully."}

@router.get("/bookings", response_model=List[BookingOut])
def get_owner_bookings(
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).join(Property).filter(
        Property.owner_id == current_user.id
    ).order_by(desc(Booking.created_at)).all()
    return [map_booking_to_out(b) for b in bookings]

@router.post("/bookings/{id}/accept")
def accept_booking(
    id: int,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    b = db.query(Booking).filter(Booking.id == id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if not b.property or (b.property.owner_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized.")

    if b.status != "pending_owner":
        raise HTTPException(status_code=400, detail=f"Booking is in '{b.status}' status, cannot accept.")

    b.status = "confirmed"
    db.commit()

    # Notify customer
    send_notification(
        db=db,
        user_id=b.customer_id,
        type_name="booking_confirmed",
        title=f"Booking Confirmed: {b.booking_code}",
        message=f"Great news! The owner of {b.property.name} has accepted your booking request. Your shoot is confirmed!",
        booking_id=b.id,
        channel="in_app"
    )

    return {"status": "confirmed", "message": "Booking confirmed successfully."}

@router.post("/bookings/{id}/reject")
def reject_booking(
    id: int,
    body: ReasonRequest,
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    b = db.query(Booking).filter(Booking.id == id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if not b.property or (b.property.owner_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized.")

    if b.status != "pending_owner":
        raise HTTPException(status_code=400, detail=f"Booking is in '{b.status}' status, cannot reject.")

    # 100% full refund
    refund = execute_booking_refund(
        db=db,
        booking=b,
        refund_amount=b.total_amount,
        reason=body.reason or "Declined by property owner",
        cancelled_by="rejection",
        actor_id=current_user.id
    )

    return {"status": "rejected", "refund_amount": refund.amount, "message": "Booking request declined and full refund issued to customer."}

@router.get("/earnings")
def get_owner_earnings(
    current_user: User = Depends(require_role("owner", "admin")),
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).join(Property).filter(
        Property.owner_id == current_user.id,
        Booking.status.in_(["confirmed", "completed"])
    ).all()

    commission_pct = settings.PLATFORM_COMMISSION_PERCENT / 100.0

    total_gross = sum(b.subtotal for b in bookings)
    platform_commissions = sum(int(round(b.subtotal * commission_pct)) for b in bookings)
    owner_net = total_gross - platform_commissions

    return {
        "total_bookings": len(bookings),
        "gross_rental": total_gross,
        "platform_commission": platform_commissions,
        "net_earnings": owner_net,
        "payout_status": "Ready for payout (Manual / RazorpayX Route)",
        "completed_shoots": sum(1 for b in bookings if b.status == "completed"),
        "upcoming_shoots": sum(1 for b in bookings if b.status == "confirmed")
    }
