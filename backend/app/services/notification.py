import os
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, Dict, Any, List
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from app.config import settings
from app.models.notification import Notification
from app.models.user import User

TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates", "email"))
jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR)) if os.path.exists(TEMPLATE_DIR) else None

class EmailChannel:
    @staticmethod
    def send(to_email: str, subject: str, html_content: str, attachment_path: Optional[str] = None) -> bool:
        # Check SendGrid first
        if settings.SENDGRID_API_KEY:
            try:
                import httpx
                headers = {"Authorization": f"Bearer {settings.SENDGRID_API_KEY}", "Content-Type": "application/json"}
                data = {
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": settings.EMAIL_FROM},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html_content}]
                }
                res = httpx.post("https://api.sendgrid.com/v3/mail/send", headers=headers, json=data, timeout=10)
                return res.status_code in (200, 202)
            except Exception:
                pass

        # Check SMTP
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            try:
                msg = MIMEMultipart()
                msg["From"] = settings.EMAIL_FROM
                msg["To"] = to_email
                msg["Subject"] = subject
                msg.attach(MIMEText(html_content, "html"))

                if attachment_path and os.path.exists(attachment_path):
                    with open(attachment_path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                    msg.attach(part)

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.send_message(msg)
                return True
            except Exception:
                return False

        # In dev mode without active credentials: log send
        print(f"[EMAIL DEV MOCK] To: {to_email} | Subject: {subject}")
        return True

class SMSChannel:
    @staticmethod
    def send(to_phone: str, message: str) -> bool:
        if not to_phone:
            return False
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                import httpx
                url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
                auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                data = {"From": settings.TWILIO_FROM_NUMBER, "To": to_phone, "Body": message}
                res = httpx.post(url, auth=auth, data=data, timeout=10)
                return res.status_code in (200, 201)
            except Exception:
                pass
        print(f"[SMS DEV MOCK] To: {to_phone} | Message: {message}")
        return True

class WhatsAppChannel:
    @staticmethod
    def send(to_phone: str, message: str) -> bool:
        if not to_phone:
            return False
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                import httpx
                url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
                auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                data = {"From": f"whatsapp:{settings.TWILIO_FROM_NUMBER}", "To": f"whatsapp:{to_phone}", "Body": message}
                res = httpx.post(url, auth=auth, data=data, timeout=10)
                return res.status_code in (200, 201)
            except Exception:
                pass
        print(f"[WHATSAPP DEV MOCK] To: {to_phone} | Message: {message}")
        return True

def send_notification(
    db: Session,
    user_id: int,
    type_name: str,
    title: str,
    message: str,
    booking_id: Optional[int] = None,
    channel: str = "in_app",
    payload: Optional[Dict[str, Any]] = None,
    attachment_path: Optional[str] = None
) -> Notification:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # Idempotency check for reminders
    if type_name.startswith("reminder_"):
        existing = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.booking_id == booking_id,
            Notification.type == type_name
        ).first()
        if existing:
            return existing

    note_payload = payload or {}
    note_payload["message"] = message

    notification = Notification(
        user_id=user_id,
        booking_id=booking_id,
        channel=channel,
        type=type_name,
        title=title,
        payload=note_payload,
        status="queued"
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Dispatch channel
    success = True
    err_str = None
    try:
        if channel == "email" and user.email:
            success = EmailChannel.send(user.email, title, f"<h3>{title}</h3><p>{message}</p>", attachment_path)
        elif channel == "sms" and user.phone:
            success = SMSChannel.send(user.phone, f"{title}: {message}")
        elif channel == "whatsapp" and user.phone:
            success = WhatsAppChannel.send(user.phone, f"*{title}*\n{message}")
        elif channel == "in_app":
            success = True
    except Exception as e:
        success = False
        err_str = str(e)

    notification.status = "sent" if success else "failed"
    notification.sent_at = datetime.datetime.utcnow() if success else None
    notification.error = err_str
    db.commit()
    return notification
