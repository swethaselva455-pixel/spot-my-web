from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.booking import Booking
from app.models.review import Review
from app.models.property import Property
from app.schemas.review import ReviewCreate, ReviewOut
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="", tags=["Reviews"])

@router.post("/bookings/{id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    id: int,
    body: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    b = db.query(Booking).filter(Booking.id == id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if b.customer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the customer who booked this shoot can submit a review.")

    if b.status not in ("completed", "confirmed"):
        raise HTTPException(status_code=400, detail="Reviews can only be submitted after completing the shoot.")

    existing = db.query(Review).filter(Review.booking_id == b.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already submitted a review for this shoot.")

    rev = Review(
        booking_id=b.id,
        property_id=b.property_id,
        customer_id=current_user.id,
        rating=body.rating,
        comment=body.comment
    )
    db.add(rev)
    db.commit()
    db.refresh(rev)

    # Recalculate property average rating
    avg = db.query(func.avg(Review.rating)).filter(Review.property_id == b.property_id).scalar()
    if avg:
        prop = db.query(Property).filter(Property.id == b.property_id).first()
        if prop:
            prop.avg_rating = round(float(avg), 1)
            db.commit()

    return ReviewOut(
        id=rev.id,
        booking_id=rev.booking_id,
        property_id=rev.property_id,
        customer_id=rev.customer_id,
        customer_name=current_user.name,
        rating=rev.rating,
        comment=rev.comment,
        created_at=rev.created_at
    )
