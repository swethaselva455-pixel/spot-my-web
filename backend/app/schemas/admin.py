from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class StatsOut(BaseModel):
    total_users: int
    pending_users: int
    total_properties: int
    pending_properties: int
    total_bookings: int
    confirmed_bookings: int
    total_revenue: int
    platform_earnings: int

class ReasonRequest(BaseModel):
    reason: str

class RefundBookingRequest(BaseModel):
    reason: Optional[str] = "Admin manual refund"

class ReportSummary(BaseModel):
    total_revenue: int
    total_gst: int
    total_platform_fee: int
    bookings_by_status: Dict[str, int]
    top_locations: List[Dict[str, Any]]
    monthly_revenue: List[Dict[str, Any]]
