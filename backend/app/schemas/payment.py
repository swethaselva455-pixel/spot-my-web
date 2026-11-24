import datetime
from typing import Optional
from pydantic import BaseModel

class CreateOrderRequest(BaseModel):
    booking_id: int

class CreateOrderResponse(BaseModel):
    razorpay_order_id: str
    razorpay_key_id: str
    amount: int # in paise
    currency: str
    booking_id: int
    booking_code: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    property_name: str

class VerifyPaymentRequest(BaseModel):
    booking_id: int
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class PaymentOut(BaseModel):
    id: int
    booking_id: int
    razorpay_order_id: str
    razorpay_payment_id: Optional[str] = None
    amount: int
    currency: str
    status: str
    method: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True
