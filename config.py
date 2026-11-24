import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

_raw_db_url = os.getenv("DATABASE_URL", "").strip()
if not _raw_db_url or _raw_db_url == "sqlite:///spotmyshoot.db":
    DB_PATH = (BASE_DIR / "spotmyshoot.db").as_posix()
    DEFAULT_DB_URI = f"sqlite:///{DB_PATH}"
else:
    DEFAULT_DB_URI = _raw_db_url

class Config:
    """Application configuration loaded from environment variables."""
    PORT = int(os.getenv("PORT", 5000))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-fallback-secret-key-1234")
    SQLALCHEMY_DATABASE_URI = DEFAULT_DB_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Business Details
    BUSINESS_NAME = os.getenv("BUSINESS_NAME", "SpotMyShoot")
    BUSINESS_TAGLINE = os.getenv("BUSINESS_TAGLINE", "Verified Shoot Spaces & Creative Studios")
    BUSINESS_EMAIL = os.getenv("BUSINESS_EMAIL", "contact@spotmyshoot.com")
    BUSINESS_PHONE = os.getenv("BUSINESS_PHONE", "+91 98765 43210")
    CURRENCY = os.getenv("CURRENCY", "INR")
    CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "₹")
    TAX_PERCENT = float(os.getenv("TAX_PERCENT", 18.0))

    # Hold and Cancellation Policies
    SLOT_HOLD_MINUTES = int(os.getenv("SLOT_HOLD_MINUTES", 10))
    FULL_REFUND_HOURS_BEFORE = int(os.getenv("FULL_REFUND_HOURS_BEFORE", 24))
    PARTIAL_REFUND_PERCENT = float(os.getenv("PARTIAL_REFUND_PERCENT", 50.0))

    # Razorpay Gateway
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "rzp_secret_placeholder")
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "rzp_webhook_placeholder")
    RAZORPAY_MOCK_MODE = os.getenv("RAZORPAY_MOCK_MODE", "True").lower() in ("true", "1", "yes")

    # SMTP Mail
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "SpotMyShoot Bookings")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "bookings@spotmyshoot.com")

    # Twilio Addon
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Default Admin
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@spotmyshoot.com")
