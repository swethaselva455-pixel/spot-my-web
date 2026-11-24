import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./spotmyshoot.db"
    SECRET_KEY: str = "spotmyshoot_super_secure_jwt_secret_key_2026_dev_mode_secret!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    RAZORPAY_KEY_ID: str = "rzp_test_spotmyshoot1234"
    RAZORPAY_KEY_SECRET: str = "rzp_secret_dummy_test_key_5678"
    RAZORPAY_WEBHOOK_SECRET: str = "rzp_whsec_dummy_webhook_secret_9012"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "SpotMyShoot <no-reply@spotmyshoot.com>"
    SENDGRID_API_KEY: Optional[str] = None

    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_SENDER_ID: str = "SPTSHT"

    STORAGE_TYPE: str = "local"
    CLOUDINARY_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = "spotmyshoot-media"

    FRONTEND_BASE_URL: str = "http://localhost:8000"
    TIMEZONE: str = "Asia/Kolkata"
    BOOKING_HOLD_MINUTES: int = 10
    PLATFORM_COMMISSION_PERCENT: float = 10.0
    GST_PERCENT: float = 18.0
    DEFAULT_BUFFER_MINUTES: int = 30
    OWNER_RESPONSE_TIMEOUT_HOURS: int = 12

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
