import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.user import User
from app.models.property import Property
from app.models.booking import Booking
from app.schemas.booking import (
    QuoteRequest, QuoteResponse, BookingCreate, BookingOut,
    CancelPreviewResponse, CancelRequest
)
from app.utils.dependencies import get_current_user, require_approved_user
from app.services.booking import calculate_quote, create_booking_hold
from app.services.refund import calculate_cancellation_refund, execute_booking_refund
from app.services.invoice import generate_invoice_pdf

router = APIRouter(prefix="/bookings", tags=["Bookings"])

def map_booking_to_out(b: Booking) -> BookingOut:
    cover = None
    if b.property and b.property.images:
        for img in b.property.images:
            if img.is_cover:
                cover = img.url
                break
        if not cover and b.property.images:
            cover = b.property.images[0].url

    return BookingOut(
        id=b.id,
        booking_code=b.booking_code,
        property_id=b.property_id,
        property_name=b.property.name if b.property else "Location",
        property_city=b.property.city if b.property else "",
        property_area=b.property.area if b.property else "",
        property_address=b.property.address if b.property else "",
        property_cover_image=cover,
        customer_id=b.customer_id,
        customer_name=b.customer.name if b.customer else "Creator",
        customer_email=b.customer.email if b.customer else "",
        customer_phone=b.customer.phone if b.customer else "",
        shoot_category=b.shoot_category,
        start_datetime=b.start_datetime,
        end_datetime=b.end_datetime,
        duration_hours=b.duration_hours,
        crew_size=b.crew_size,
        special_requests=b.special_requests,
        subtotal=b.subtotal,
        gst_amount=b.gst_amount,
        platform_fee=b.platform_fee,
        total_amount=b.total_amount,
        status=b.status,
        hold_expires_at=b.hold_expires_at,
        cancellation_reason=b.cancellation_reason,
        created_at=b.created_at
    )

@router.post("/quote", response_model=QuoteResponse)
def get_quote(body: QuoteRequest, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == body.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found.")
    quote = calculate_quote(prop, body.duration_hours)
    return QuoteResponse(**quote)

@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    body: BookingCreate,
    current_user: User = Depends(require_approved_user),
    db: Session = Depends(get_db)
):
    booking = create_booking_hold(
        db=db,
        customer_id=current_user.id,
        property_id=body.property_id,
        shoot_category=body.shoot_category,
        date_str=body.date,
        start_time_str=body.start_time,
        duration_hours=body.duration_hours,
        crew_size=body.crew_size,
        special_requests=body.special_requests
    )
    return map_booking_to_out(booking)

@router.get("/my", response_model=List[BookingOut])
def get_my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).filter(
        Booking.customer_id == current_user.id
    ).order_by(desc(Booking.created_at)).all()
    return [map_booking_to_out(b) for b in bookings]

@router.get("/{id}", response_model=BookingOut)
def get_booking(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    b = db.query(Booking).filter(Booking.id == id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # Authorization check
    is_owner = b.property and b.property.owner_id == current_user.id
    if b.customer_id != current_user.id and not is_owner and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this booking.")

    return map_booking_to_out(b)

@router.get("/{id}/cancel-preview", response_model=CancelPreviewResponse)
def preview_cancellation(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    b = db.query(Booking).filter(Booking.id == id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if b.customer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking.")

    if b.status in ("cancelled_by_customer", "cancelled_by_owner", "rejected", "refunded", "expired"):
        raise HTTPException(status_code=400, detail=f"Booking is already in status '{b.status}'.")

    preview = calculate_cancellation_refund(b, cancelled_by="customer")
    return CancelPreviewResponse(
        booking_id=b.id,
        booking_code=b.booking_code,
        status=b.status,
        total_amount=b.total_amount,
        hours_until_shoot=preview["hours_until_shoot"],
        cancellation_policy=preview["cancellation_policy"],
        refund_percentage=preview["refund_percentage"],
        refund_amount=preview["refund_amount"],
        platform_fee_retained=preview["platform_fee_retained"],
        message=preview["message"]
    )

@router.post("/{id}/cancel")
def cancel_booking(
    id: int,
    body: CancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    b = db.query(Booking).filter(Booking.id == id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if b.customer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking.")

    if b.status not in ("hold", "pending_owner", "confirmed"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel booking with current status '{b.status}'.")

    # If status is still 'hold' (unpaid) -> simply expire/cancel without payment refund
    if b.status == "hold":
        b.status = "cancelled_by_customer"
        b.cancellation_reason = body.reason
        db.commit()
        return {"message": "Hold booking cancelled.", "refund_amount": 0}

    # If paid (pending_owner or confirmed) -> calculate refund and execute
    calc = calculate_cancellation_refund(b, cancelled_by="customer")
    refund = execute_booking_refund(
        db=db,
        booking=b,
        refund_amount=calc["refund_amount"],
        reason=body.reason or calc["message"],
        cancelled_by="customer",
        actor_id=current_user.id
    )

    return {
        "message": "Booking successfully cancelled.",
        "refund_amount": refund.amount,
        "refund_id": refund.razorpay_refund_id,
        "status": b.status
    }

@router.get("/{id}/invoice")
def get_invoice(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    b = db.query(Booking).filter(Booking.id == id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")

    is_owner = b.property and b.property.owner_id == current_user.id
    if b.customer_id != current_user.id and not is_owner and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized.")

    pdf_path = generate_invoice_pdf(b)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="Could not generate invoice PDF.")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"Invoice_{b.booking_code.replace('#', '')}.pdf"
    )
