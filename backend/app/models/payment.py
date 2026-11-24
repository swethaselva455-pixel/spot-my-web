import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    razorpay_order_id = Column(String(100), unique=True, index=True, nullable=False)
    razorpay_payment_id = Column(String(100), unique=True, index=True, nullable=True)
    razorpay_signature = Column(String(255), nullable=True)
    amount = Column(Integer, nullable=False) # INR paise or INR
    currency = Column(String(10), default="INR")
    # status: created, authorized, captured, failed, refunded, partially_refunded
    status = Column(String(30), default="created", index=True, nullable=False)
    method = Column(String(50), nullable=True) # upi, card, netbanking, wallet
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    booking = relationship("Booking", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment", cascade="all, delete-orphan")


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Integer, nullable=False) # INR
    razorpay_refund_id = Column(String(100), unique=True, index=True, nullable=True)
    status = Column(String(30), default="processed") # processed, failed, pending
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    payment = relationship("Payment", back_populates="refunds")
    booking = relationship("Booking", back_populates="refunds")
