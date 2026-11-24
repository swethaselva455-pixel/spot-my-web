import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from app.database import get_db
from app.models.property import Property, PropertyImage, PropertyCategory, AvailabilityRule
from app.models.review import Review
from app.schemas.property import (
    PropertyDetailOut, PropertyListItem, AvailabilityRuleOut
)
from app.schemas.review import ReviewOut
from app.services.availability import (
    get_day_availability, get_month_calendar_summary
)

router = APIRouter(prefix="/properties", tags=["Properties"])

@router.get("", response_model=List[PropertyListItem])
def list_properties(
    q: Optional[str] = Query(None, description="Search query across name, city, area"),
    city: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    date: Optional[str] = Query(None, description="Filter properties available on YYYY-MM-DD"),
    sort: Optional[str] = Query("recommended", description="recommended, low, high"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Property).filter(
        Property.approval_status == "approved",
        Property.is_published == True
    )

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Property.name.ilike(search_pattern),
                Property.city.ilike(search_pattern),
                Property.area.ilike(search_pattern),
                Property.description.ilike(search_pattern)
            )
        )

    if city and city.lower() != "all":
        query = query.filter(Property.city.ilike(f"%{city.strip()}%"))

    if type and type.lower() != "all":
        query = query.filter(Property.property_type.ilike(f"%{type.strip()}%"))

    if category and category.lower() != "all":
        query = query.join(Property.categories).filter(PropertyCategory.category.ilike(f"%{category.strip()}%"))

    if min_price is not None:
        query = query.filter(Property.hourly_price >= min_price)

    if max_price is not None:
        query = query.filter(Property.hourly_price <= max_price)

    # Sort
    if sort == "low":
        query = query.order_by(asc(Property.hourly_price))
    elif sort == "high":
        query = query.order_by(desc(Property.hourly_price))
    else: # recommended: by rating and recent
        query = query.order_by(desc(Property.avg_rating), desc(Property.id))

    properties = query.offset((page - 1) * page_size).limit(page_size).all()

    # Filter by date if provided
    result = []
    for p in properties:
        if date:
            slots = get_day_availability(db, p, date)
            if not any(s["available"] for s in slots):
                continue

        cover = None
        for img in p.images:
            if img.is_cover:
                cover = img.url
                break
        if not cover and p.images:
            cover = p.images[0].url

        cats = [c.category for c in p.categories]

        result.append(
            PropertyListItem(
                id=p.id,
                name=p.name,
                city=p.city,
                area=p.area,
                property_type=p.property_type,
                hourly_price=p.hourly_price,
                avg_rating=p.avg_rating,
                cover_image=cover,
                categories=cats,
                approval_status=p.approval_status,
                is_published=p.is_published,
                min_hours=p.min_hours,
                max_crew_size=p.max_crew_size
            )
        )

    return result

@router.get("/{id}", response_model=PropertyDetailOut)
def get_property(id: int, db: Session = Depends(get_db)):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")

    cats = [c.category for c in p.categories]
    return PropertyDetailOut(
        id=p.id,
        owner_id=p.owner_id,
        owner_name=p.owner.name if p.owner else "Property Host",
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

@router.get("/{id}/reviews", response_model=List[ReviewOut])
def get_property_reviews(id: int, db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.property_id == id).order_by(desc(Review.created_at)).all()
    return [
        ReviewOut(
            id=r.id,
            booking_id=r.booking_id,
            property_id=r.property_id,
            customer_id=r.customer_id,
            customer_name=r.customer.name if r.customer else "Creator",
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at
        )
        for r in reviews
    ]

@router.get("/{id}/availability")
def get_availability(id: int, date: str = Query(..., description="Date in YYYY-MM-DD format"), db: Session = Depends(get_db)):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")
    try:
        slots = get_day_availability(db, p, date)
        return {"date": date, "slots": slots}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format or error: {str(e)}")

@router.get("/{id}/calendar")
def get_calendar(id: int, month: str = Query(..., description="Month in YYYY-MM format"), db: Session = Depends(get_db)):
    p = db.query(Property).filter(Property.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Property not found.")
    try:
        days = get_month_calendar_summary(db, p, month)
        return {"month": month, "days": days}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid month format: {str(e)}")
