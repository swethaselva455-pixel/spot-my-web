import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class NotificationOut(BaseModel):
    id: int
    user_id: int
    booking_id: Optional[int] = None
    channel: str
    type: str
    title: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    status: str
    sent_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class NotificationPreference(BaseModel):
    email: bool = True
    sms: bool = True
    whatsapp: bool = True
