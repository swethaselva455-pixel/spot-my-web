import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_code = Column(String(30), unique=True, index=True, nullable=False) # e.g. #SMS-1082
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    shoot_category = Column(String(100), nullable=False) # Pre-wedding, Fashion, etc.
    start_datetime = Column(DateTime, nullable=False, index=True) # UTC
    end_datetime = Column(DateTime, nullable=False, index=True) # UTC
    duration_hours = Column(Integer, nullable=False)
    crew_size = Column(Integer, default=5)
    special_requests = Column(Text, nullable=True)
    
    # Financial breakdown in INR (Integers)
    subtotal = Column(Integer, nullable=False)
    gst_amount = Column(Integer, nullable=False)
    platform_fee = Column(Integer, nullable=False)
    total_amount = Column(Integer, nullable=False)

    # Status: hold, pending_owner, confirmed, rejected, cancelled_by_customer, cancelled_by_owner, completed, expired, refunded
    status = Column(String(30), default="hold", index=True, nullable=False)
    hold_expires_at = Column(DateTime, nullable=True, index=True) # UTC
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    property = relationship("Property", back_populates="bookings")
    customer = relationship("User", back_populates="bookings", foreign_keys=[customer_id])
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")
    refunds = relationship("Refund", back_populates="booking", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="booking", uselist=False)

# Composite index for quick availability overlap checks
Index("ix_bookings_property_dates_status", Booking.property_id, Booking.start_datetime, Booking.end_datetime, Booking.status)
