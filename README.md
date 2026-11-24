# SpotMyShoot — Verified Shoot Spaces & Studio Booking System

A lightweight, production-ready, full-stack booking website built with **Python Flask**, **SQLite (Flask-SQLAlchemy)**, **Razorpay Payments**, **APScheduler**, and **Vanilla HTML/CSS/JS**.

Designed for photography studios, shoot locations, creative spaces, film sets, salon suites, turf arenas, and tutor cabins. Runs locally with **one command**.

---

## 📁 Full Folder Structure

```
spotmyshoot/
├── .env.example              # Template environment variables
├── .env                      # Local configuration file (never committed to git)
├── requirements.txt          # Python dependencies
├── run.py                    # One-command runner (auto-initializes & seeds DB)
├── app.py                    # Main Flask application, routes, and error handlers
├── models.py                 # SQLAlchemy models (Service, Slot, Booking, Payment, AdminUser)
├── config.py                 # Configuration loader from .env
├── seed.py                   # Database seeder (default admin, sample spaces, 14-day slots)
├── test_app.py               # Automated end-to-end integration test suite
├── static/
│   ├── style.css             # Responsive modern stylesheet (Brand color: #2563eb)
│   └── app.js                # Dynamic slot loader, 10-min hold timer, Razorpay checkout
├── templates/
│   ├── base.html             # Base layout with header, navigation, flash messages, footer
│   ├── index.html            # Landing page with hero, spaces grid, and workflow
│   ├── services.html         # Shoot locations & spaces catalog
│   ├── book.html             # Live date calendar & interactive time slots picker
│   ├── checkout.html         # 10-minute hold lock summary & Razorpay payment modal
│   ├── payment_success.html  # Booking confirmation receipt with print view
│   ├── my_booking.html       # Self-service lookup, cancellation & automated refund
│   ├── admin_login.html      # Secure admin login form
│   └── admin_dashboard.html  # Operations dashboard, revenue metrics & slot blocker
└── spotmyshoot.db            # SQLite database (auto-generated on first launch)
```

---

## ⚡ 1. Quick Start (Run in One Command)

### Prerequisites
- Python 3.10+ installed
- Pip package manager

### Installation
1. Open a terminal in the project directory:
   ```bash
   cd spotmyshoot
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python run.py
   ```
4. Open your browser:
   - **Public Website:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
   - **Admin Console:** [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)
     - Username: `admin`
     - Password: `admin123`

---

## ⚙️ 2. Environment Configuration (`.env`)

Copy `.env.example` to `.env`:
```ini
# App Configuration
SECRET_KEY=dev-secret-key-change-in-production-12345
FLASK_ENV=development
PORT=5000
DATABASE_URL=sqlite:///spotmyshoot.db

# Business Details
BUSINESS_NAME=SpotMyShoot
BUSINESS_TAGLINE=Verified Shoot Spaces & Creative Studios
BUSINESS_EMAIL=contact@spotmyshoot.com
BUSINESS_PHONE=+91 98765 43210
CURRENCY=INR
CURRENCY_SYMBOL=₹
TAX_PERCENT=18

# Booking & Cancellation Policy
SLOT_HOLD_MINUTES=10
FULL_REFUND_HOURS_BEFORE=24
PARTIAL_REFUND_PERCENT=50

# Razorpay Payment Gateway (Test Mode)
# Set RAZORPAY_MOCK_MODE=True to test the full checkout flow without live API keys
RAZORPAY_KEY_ID=rzp_test_YourKeyIdHere
RAZORPAY_KEY_SECRET=YourKeySecretHere
RAZORPAY_WEBHOOK_SECRET=YourWebhookSecret
RAZORPAY_MOCK_MODE=True

# Email Notifications (Gmail SMTP with App Password)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=True
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-gmail-app-password
SMTP_FROM_NAME=SpotMyShoot Bookings
SMTP_FROM_EMAIL=your-email@gmail.com

# Optional Twilio SMS Add-on
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# Default Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@spotmyshoot.com
```

---

## 💳 3. How to Test Payments

### Option A: Built-in Instant Sandbox Mode (Default)
When `RAZORPAY_MOCK_MODE=True` in `.env`:
1. Go to [http://127.0.0.1:5000/book](http://127.0.0.1:5000/book)
2. Pick any space, date, and open slot.
3. Enter your contact details and click **Proceed to Checkout**.
4. On the checkout page, you will see a prominent **Simulate Successful Payment (Test)** button.
5. Click it to verify signature processing, database confirmation, instant receipt generation, and confirmation email dispatch.

### Option B: Razorpay Official Test Gateway
1. Set `RAZORPAY_MOCK_MODE=False` in `.env`.
2. Add your Razorpay Test Key ID and Secret from your Razorpay Dashboard (`rzp_test_...`).
3. During checkout, the Razorpay standard modal will open. Use Razorpay test credentials:
   - **UPI:** Success UPI ID `success@razorpay`
   - **Card Number:** `4111 1111 1111 1111`
   - **Expiry:** Any future date (e.g. `12/28`)
   - **CVV:** `123`
   - **OTP:** Any 4-digit code (e.g. `1234`)

---

## 📧 4. How to Test Email Reminders

### Local Console Simulation (Default)
If `SMTP_USER` and `SMTP_PASSWORD` are blank in `.env`, all confirmation, reminder, and cancellation emails are logged directly to your terminal console with complete HTML and subject lines so you can test without needing external credentials.

### Live Gmail SMTP Delivery
1. Enable **2-Step Verification** on your Google Account.
2. Go to **Google Account > Security > App Passwords**.
3. Generate a new app password for "Mail".
4. Paste your Gmail address into `SMTP_USER` and the 16-character password into `SMTP_PASSWORD` in `.env`.
5. APScheduler runs background jobs every 60 seconds:
   - Releases expired 10-minute holds.
   - Automatically delivers 24-hour reminder emails when shoots are 23-25 hours away.
   - Delivers 1-hour reminder emails when shoots are 45-75 minutes away.

---

## 🔄 5. Cancellation & Refund Policy

1. Users can look up any booking under `/my-booking` by providing their **Booking Reference** (e.g. `SMS-5D6B80`) and **Customer Email**.
2. **Refund Rules:**
   - **24+ Hours Before Slot:** 100% full automatic refund.
   - **Within 24 Hours of Slot:** 50% partial automatic refund.
   - **Past Appointment:** 0% refund.
3. When cancelled, the refund is processed via the Razorpay API (or recorded in mock mode), the booking is marked `cancelled`, and the slot **immediately becomes available** for other customers on the calendar.

---

## 🚀 6. Free Tier Deployment Guide

### Deploying on Render (Free)
1. Push your repository to GitHub.
2. Log in to [render.com](https://render.com) and click **New > Web Service**.
3. Connect your GitHub repository.
4. Settings:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app` or `python run.py`
5. In **Environment Variables**, add the keys from your `.env` file (`SECRET_KEY`, `RAZORPAY_KEY_ID`, etc.).
6. Click **Deploy Web Service**.

### Deploying on PythonAnywhere (Free)
1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com).
2. Open a Bash console and clone your repository or upload the files.
3. Create a virtualenv and install dependencies:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 myenv
   pip install -r requirements.txt
   ```
4. Under the **Web** tab, click **Add a new web app**, choose **Manual configuration**, and select Python 3.10.
5. In the **Virtualenv** section, enter the path to `myenv`.
6. Edit the **WSGI configuration file**:
   ```python
   import sys
   import os

   project_home = '/home/yourusername/spotmyshoot'
   if project_home not in sys.path:
       sys.path = [project_home] + sys.path

   from app import app as application
   ```
7. Click **Reload** to launch your live site.

---

## 🎨 7. How to Customize

1. **Website Name & Branding:**
   - Update `BUSINESS_NAME`, `BUSINESS_TAGLINE`, `BUSINESS_EMAIL`, and `BUSINESS_PHONE` in `.env`.
   - Update the logo mark in `templates/base.html` (e.g. `<span>◎</span>`).

2. **Colors & Styling:**
   - Open `static/style.css` and change `:root` variables:
     - `--primary: #2563eb;` (Change to your brand color, e.g., `#059669` for emerald turf, `#db2777` for salon pink, `#4f46e5` for tutor indigo).

3. **Services, Spaces & Pricing:**
   - Edit `sample_services` in `seed.py` or use the Admin Dashboard to add new custom shoot locations, hourly rates, and session durations.

4. **Slot Timing & Capacity:**
   - In `seed.py`, edit `slot_times` to adjust daily slots (e.g., `[("06:00", "07:00"), ("07:00", "08:00")]` for turf / sports).
   - Change `capacity` per slot in `models.py` or through the admin panel.

5. **Cancellation & Tax Percent:**
   - Change `FULL_REFUND_HOURS_BEFORE=24` and `PARTIAL_REFUND_PERCENT=50` in `.env`.
   - Change `TAX_PERCENT=18` in `.env` to match your local tax structure.

---

## 🧪 8. Automated Tests

Run the complete integration test suite at any time:
```bash
python test_app.py
```
Verifies public pages, dynamic availability API, 10-minute hold lock, payment verification, cancellation refund calculation, and admin dashboard controls.
