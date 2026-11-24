import os
from config import Config
from app import app
from seed import seed_database
from services.scheduler_service import init_scheduler

def launch():
    # Automatically seed fresh database if empty and start the application server with background jobs.
    with app.app_context():
        from models import Service, AdminUser
        if Service.query.count() == 0 or not AdminUser.query.filter_by(username=Config.ADMIN_USERNAME).first():
            print("[Startup] Initializing and seeding database...")
            seed_database()

    init_scheduler(app)

    print("\n" + "=" * 65)
    print(f"  {Config.BUSINESS_NAME} — {Config.BUSINESS_TAGLINE}")
    print("=" * 65)
    print(f"  * Website URL:     http://127.0.0.1:{Config.PORT or 5000}")
    print(f"  * Admin Login:     http://127.0.0.1:{Config.PORT or 5000}/admin/login")
    print(f"  * Admin User:      {Config.ADMIN_USERNAME}")
    print(f"  * Admin Password:  {Config.ADMIN_PASSWORD}")
    print(f"  * Payment Gateway: {'Simulated Test Sandbox (Instant)' if Config.RAZORPAY_MOCK_MODE else 'Live Razorpay API'}")
    print(f"  * Email Reminders: {'Gmail SMTP Configured' if Config.SMTP_USER else 'Local Console Log Simulation'}")
    print("=" * 65 + "\n")

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == '__main__':
    launch()
