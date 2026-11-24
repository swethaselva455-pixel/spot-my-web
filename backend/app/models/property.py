import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, Float, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    city = Column(String(100), nullable=False, index=True)
    area = Column(String(100), nullable=False, index=True)
    address = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    property_type = Column(String(50), nullable=False, index=True) # villa, studio, beach, garden, heritage, other
    hourly_price = Column(Integer, nullable=False) # stored in INR (or paise / integer INR)
    min_hours = Column(Integer, default=2)
    max_hours = Column(Integer, default=12)
    max_crew_size = Column(Integer, default=25)
    amenities = Column(JSON, default=list) # e.g. ["Dressing Room", "Air Conditioning", "WiFi", "Parking"]
    rules_text = Column(Text, nullable=True)
    cancellation_policy = Column(String(20), default="moderate") # flexible, moderate, strict
    approval_status = Column(String(20), default="pending", index=True) # pending, approved, rejected
    is_published = Column(Boolean, default=False, index=True)
    auto_accept = Column(Boolean, default=False)
    rejection_reason = Column(Text, nullable=True)
    avg_rating = Column(Float, default=0.0)
    buffer_minutes = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="properties")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan", order_by="PropertyImage.sort_order")
    categories = relationship("PropertyCategory", back_populates="property", cascade="all, delete-orphan")
    availability_rules = relationship("AvailabilityRule", back_populates="property", cascade="all, delete-orphan")
    blocked_slots = relationship("BlockedSlot", back_populates="property", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="property")
    reviews = relationship("Review", back_populates="property")


class PropertyImage(Base):
    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    is_cover = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    property = relationship("Property", back_populates="images")


class PropertyCategory(Base):
    __tablename__ = "property_categories"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True) # Maternity, Pre-wedding, Wedding, Reels, Cinematography, Fashion

    property = relationship("Property", back_populates="categories")


class AvailabilityRule(Base):
    __tablename__ = "availability_rules"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False) # 0=Monday, 6=Sunday
    open_time = Column(Time, nullable=False)
    close_time = Column(Time, nullable=False)

    property = relationship("Property", back_populates="availability_rules")


class BlockedSlot(Base):
    __tablename__ = "blocked_slots"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    start_datetime = Column(DateTime, nullable=False, index=True)
    end_datetime = Column(DateTime, nullable=False, index=True)
    reason = Column(String(255), default="Maintenance / Owner Block")

    property = relationship("Property", back_populates="blocked_slots")
