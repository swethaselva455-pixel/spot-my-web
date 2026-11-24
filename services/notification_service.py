import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import Config

def send_email_smtp(to_email, subject, html_content, text_content=None):
    # Dispatch an HTML email via configured SMTP credentials or log cleanly to console for local testing.
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        print("\n" + "="*60)
        print(f"[EMAIL SIMULATION] To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{text_content or html_content}")
        print("="*60 + "\n")
        return True

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{Config.SMTP_FROM_NAME} <{Config.SMTP_FROM_EMAIL}>"
        msg['To'] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10) as server:
            if Config.SMTP_USE_TLS:
                server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_FROM_EMAIL, to_email, msg.as_string())
        print(f"[Email Sent] Successfully delivered to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[Email Error] Could not send email to {to_email}: {str(e)}")
        return False

def send_booking_confirmation_email(booking):
    # Compose and send an instant confirmation receipt email upon successful booking payment.
    service_name = booking.service.name if booking.service else "Shoot Studio"
    slot_date = booking.slot.slot_date.strftime('%A, %d %B %Y') if booking.slot else ""
    slot_time = f"{booking.slot.start_time} - {booking.slot.end_time}" if booking.slot else ""

    subject = f"Booking Confirmed: {booking.booking_reference} - {Config.BUSINESS_NAME}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1e293b; line-height: 1.6; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #2563eb; color: #ffffff; padding: 24px; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">{Config.BUSINESS_NAME}</h1>
            <p style="margin: 4px 0 0; opacity: 0.9;">Booking Confirmation Receipt</p>
        </div>
        <div style="padding: 24px;">
            <p>Hi <strong>{booking.customer_name}</strong>,</p>
            <p>Your booking has been confirmed! Here are your appointment details:</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0; background: #f8fafc; border-radius: 6px;">
                <tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Booking ID:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{booking.booking_reference}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Location / Service:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{service_name}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Date:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{slot_date}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Time Slot:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{slot_time}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">Amount Paid:</td><td style="padding: 10px; border-bottom: 1px solid #e2e8f0; color: #16a34a; font-weight: bold;">{Config.CURRENCY_SYMBOL}{booking.total_amount:.2f} (incl. taxes)</td></tr>
                <tr><td style="padding: 10px; font-weight: bold;">Status:</td><td style="padding: 10px;"><span style="background: #dcfce7; color: #166534; padding: 4px 8px; border-radius: 4px; font-weight: bold;">Confirmed</span></td></tr>
            </table>

            <p style="margin-top: 24px; font-size: 14px; color: #64748b;">
                Need to view or manage your booking? Visit our portal using your Booking ID <strong>{booking.booking_reference}</strong> and email <strong>{booking.customer_email}</strong>.
            </p>
        </div>
        <div style="background: #f1f5f9; padding: 16px; text-align: center; font-size: 12px; color: #64748b;">
            {Config.BUSINESS_NAME} &bull; {Config.BUSINESS_EMAIL} &bull; {Config.BUSINESS_PHONE}
        </div>
    </div>
    """
    return send_email_smtp(booking.customer_email, subject, html)

def send_reminder_email(booking, hours_label):
    # Send a reminder notification email to the customer before their scheduled shoot.
    service_name = booking.service.name if booking.service else "Shoot Studio"
    slot_date = booking.slot.slot_date.strftime('%A, %d %B %Y') if booking.slot else ""
    slot_time = f"{booking.slot.start_time} - {booking.slot.end_time}" if booking.slot else ""

    subject = f"Reminder: Your shoot appointment is in {hours_label} - {Config.BUSINESS_NAME}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1e293b; line-height: 1.6; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #2563eb; color: #ffffff; padding: 20px; text-align: center;">
            <h2 style="margin: 0;">Upcoming Shoot Reminder ({hours_label})</h2>
        </div>
        <div style="padding: 24px;">
            <p>Hi <strong>{booking.customer_name}</strong>,</p>
            <p>This is a quick reminder that your booking at <strong>{Config.BUSINESS_NAME}</strong> starts in <strong>{hours_label}</strong>!</p>
            
            <div style="background: #f8fafc; border-left: 4px solid #2563eb; padding: 16px; margin: 20px 0;">
                <p style="margin: 0 0 8px;"><strong>Booking ID:</strong> {booking.booking_reference}</p>
                <p style="margin: 0 0 8px;"><strong>Location:</strong> {service_name}</p>
                <p style="margin: 0 0 8px;"><strong>Date:</strong> {slot_date}</p>
                <p style="margin: 0;"><strong>Time Slot:</strong> {slot_time}</p>
            </div>
            
            <p>Please arrive 10 minutes prior to your slot time to ensure smooth setup.</p>
        </div>
        <div style="background: #f1f5f9; padding: 14px; text-align: center; font-size: 12px; color: #64748b;">
            Questions? Contact {Config.BUSINESS_PHONE} or reply to {Config.BUSINESS_EMAIL}
        </div>
    </div>
    """
    return send_email_smtp(booking.customer_email, subject, html)

def send_cancellation_email(booking, refund_amount):
    # Send a cancellation acknowledgment email with refund details to the customer.
    subject = f"Booking Cancelled: {booking.booking_reference} - {Config.BUSINESS_NAME}"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1e293b; line-height: 1.6; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #ef4444; color: #ffffff; padding: 20px; text-align: center;">
            <h2 style="margin: 0;">Booking Cancellation</h2>
        </div>
        <div style="padding: 24px;">
            <p>Hi <strong>{booking.customer_name}</strong>,</p>
            <p>Your booking <strong>{booking.booking_reference}</strong> has been cancelled as requested.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0; background: #fef2f2; border-radius: 6px;">
                <tr><td style="padding: 10px; border-bottom: 1px solid #fecaca; font-weight: bold;">Booking ID:</td><td style="padding: 10px; border-bottom: 1px solid #fecaca;">{booking.booking_reference}</td></tr>
                <tr><td style="padding: 10px; border-bottom: 1px solid #fecaca; font-weight: bold;">Reason:</td><td style="padding: 10px; border-bottom: 1px solid #fecaca;">{booking.cancellation_reason or 'Customer request'}</td></tr>
                <tr><td style="padding: 10px; font-weight: bold;">Refund Amount:</td><td style="padding: 10px; font-weight: bold; color: #dc2626;">{Config.CURRENCY_SYMBOL}{refund_amount:.2f}</td></tr>
            </table>

            <p style="font-size: 14px; color: #64748b;">
                Eligible refunds are processed to your original payment method within 5-7 business days per bank policies.
            </p>
        </div>
    </div>
    """
    return send_email_smtp(booking.customer_email, subject, html)

def send_sms_twilio(phone, message):
    # Send an optional SMS or WhatsApp notification via Twilio when API keys are configured.
    if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN or not Config.TWILIO_PHONE_NUMBER:
        print(f"[SMS SIMULATION] To: {phone} | Message: {message}")
        return True

    try:
        import requests
        url = f"https://api.twilio.com/2010-04-01/Accounts/{Config.TWILIO_ACCOUNT_SID}/Messages.json"
        data = {
            'From': Config.TWILIO_PHONE_NUMBER,
            'To': phone,
            'Body': message
        }
        res = requests.post(url, data=data, auth=(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN), timeout=8)
        return res.status_code in (200, 201)
    except Exception as e:
        print(f"[Twilio SMS Error] {e}")
        return False
