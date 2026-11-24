import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

class ReviewOut(BaseModel):
    id: int
    booking_id: int
    property_id: int
    customer_id: int
    customer_name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True
