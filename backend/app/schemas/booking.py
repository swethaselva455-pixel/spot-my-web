import datetime
from typing import Optional
from pydantic import BaseModel, Field

class QuoteRequest(BaseModel):
    property_id: int
    date: str # "YYYY-MM-DD"
    start_time: str # "HH:MM"
    duration_hours: int = Field(..., ge=1, le=24)

class QuoteResponse(BaseModel):
    property_id: int
    property_name: str
    hourly_price: int
    duration_hours: int
    subtotal: int
    gst_percent: float
    gst_amount: int
    platform_fee: int
    total_amount: int
    cancellation_policy: str

class BookingCreate(BaseModel):
    property_id: int
    shoot_category: str
    date: str # "YYYY-MM-DD"
    start_time: str # "HH:MM"
    duration_hours: int = Field(..., ge=1, le=24)
    crew_size: int = Field(..., ge=1)
    special_requests: Optional[str] = None

class BookingOut(BaseModel):
    id: int
    booking_code: str
    property_id: int
    property_name: str
    property_city: str
    property_area: str
    property_address: Optional[str] = None
    property_cover_image: Optional[str] = None
    customer_id: int
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    shoot_category: str
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    duration_hours: int
    crew_size: int
    special_requests: Optional[str] = None
    subtotal: int
    gst_amount: int
    platform_fee: int
    total_amount: int
    status: str
    hold_expires_at: Optional[datetime.datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class CancelPreviewResponse(BaseModel):
    booking_id: int
    booking_code: str
    status: str
    total_amount: int
    hours_until_shoot: float
    cancellation_policy: str
    refund_percentage: int
    refund_amount: int
    platform_fee_retained: int
    message: str

class CancelRequest(BaseModel):
    reason: Optional[str] = "Customer requested cancellation"
