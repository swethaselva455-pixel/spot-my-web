import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field

class AvailabilityRuleBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    open_time: str # "09:00"
    close_time: str # "20:00"

class AvailabilityRuleOut(AvailabilityRuleBase):
    id: int
    class Config:
        from_attributes = True

class BlockedSlotBase(BaseModel):
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    reason: Optional[str] = "Owner Block"

class BlockedSlotOut(BlockedSlotBase):
    id: int
    property_id: int
    class Config:
        from_attributes = True

class PropertyImageOut(BaseModel):
    id: int
    url: str
    is_cover: bool
    sort_order: int
    class Config:
        from_attributes = True

class PropertyCategoryOut(BaseModel):
    id: int
    category: str
    class Config:
        from_attributes = True

class PropertyCreateUpdate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    city: str
    area: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    property_type: str # villa, studio, beach, garden, heritage, other
    hourly_price: int = Field(..., gt=0)
    min_hours: int = Field(2, ge=1)
    max_hours: int = Field(12, le=24)
    max_crew_size: int = Field(25, ge=1)
    amenities: List[str] = []
    rules_text: Optional[str] = None
    cancellation_policy: str = "moderate" # flexible, moderate, strict
    categories: List[str] = [] # Maternity, Pre-wedding, Wedding, Reels, Cinematography, Fashion
    auto_accept: bool = False
    buffer_minutes: int = 30

class PropertyListItem(BaseModel):
    id: int
    name: str
    city: str
    area: str
    property_type: str
    hourly_price: int
    avg_rating: float
    cover_image: Optional[str] = None
    categories: List[str] = []
    approval_status: str
    is_published: bool
    min_hours: int
    max_crew_size: int

    class Config:
        from_attributes = True

class PropertyDetailOut(BaseModel):
    id: int
    owner_id: int
    owner_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    city: str
    area: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    property_type: str
    hourly_price: int
    min_hours: int
    max_hours: int
    max_crew_size: int
    amenities: List[str] = []
    rules_text: Optional[str] = None
    cancellation_policy: str
    approval_status: str
    is_published: bool
    auto_accept: bool
    avg_rating: float
    buffer_minutes: int
    created_at: datetime.datetime
    images: List[PropertyImageOut] = []
    categories: List[str] = []
    availability_rules: List[AvailabilityRuleOut] = []

    class Config:
        from_attributes = True
