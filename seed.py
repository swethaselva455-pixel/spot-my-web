from datetime import date, timedelta
from flask import Flask
from config import Config
from models import db, Service, Slot, Booking, Payment, AdminUser

def create_app():
    # Instantiate a lightweight Flask application for database operations.
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def seed_database():
    # Populate the database with default admin credentials, shoot locations, and initial calendar slots.
    app = create_app()
    with app.app_context():
        db.create_all()

        # 1. Admin User
        admin = AdminUser.query.filter_by(username=Config.ADMIN_USERNAME).first()
        if not admin:
            admin = AdminUser(
                username=Config.ADMIN_USERNAME,
                email=Config.ADMIN_EMAIL
            )
            admin.set_password(Config.ADMIN_PASSWORD)
            db.session.add(admin)
            print(f"[Seed] Created admin: {Config.ADMIN_USERNAME} / {Config.ADMIN_PASSWORD}")

        # 2. Services
        existing_count = Service.query.count()
        if existing_count == 0:
            sample_services = [
                Service(
                    name="Casa Verde Villa - Poolside & Lawn",
                    category="Villa",
                    description="Contemporary light-filled villa featuring manicured lawns, open courtyard, and infinity poolside for pre-wedding and fashion shoots.",
                    price=2500.0,
                    duration_hours=2,
                    image_url="https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80",
                    is_active=True
                ),
                Service(
                    name="Northlight Creative Studio - Cyclorama",
                    category="Studio",
                    description="Sound-dampened white cyclorama infinity cove with Profoto lighting grid, motorized backdrops, and private vanity room.",
                    price=1800.0,
                    duration_hours=2,
                    image_url="https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=800&q=80",
                    is_active=True
                ),
                Service(
                    name="Marina Dunes Coastal Pavilion",
                    category="Beach & Outdoor",
                    description="Seaside open-air pavilion overlooking golden sand dunes and coastal sunsets, ideal for music videos, maternity, and cinematic reels.",
                    price=2200.0,
                    duration_hours=2,
                    image_url="https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&q=80",
                    is_active=True
                ),
                Service(
                    name="The Botanical Glasshouse Conservatory",
                    category="Garden",
                    description="European-inspired glasshouse conservatory filled with exotic plants and all-day soft diffused natural daylight.",
                    price=3000.0,
                    duration_hours=2,
                    image_url="https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80",
                    is_active=True
                ),
                Service(
                    name="Adyar Chettinad Heritage Courtyard",
                    category="Heritage",
                    description="Authentic teakwood pillars, carved stone corridors, and antique wooden swings for traditional wedding and ethnic portraits.",
                    price=3500.0,
                    duration_hours=2,
                    image_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=800&q=80",
                    is_active=True
                ),
                Service(
                    name="Skyline Industrial Loft & Terrace",
                    category="Loft",
                    description="Raw exposed brick walls, 14-foot steel-frame industrial windows, and weathered concrete floors for editorial and lookbooks.",
                    price=2000.0,
                    duration_hours=2,
                    image_url="https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=800&q=80",
                    is_active=True
                )
            ]
            db.session.add_all(sample_services)
            db.session.commit()
            print(f"[Seed] Added {len(sample_services)} services.")

        # 3. Slots for the next 14 days
        services = Service.query.all()
        slot_times = [
            ("09:00", "11:00"),
            ("11:30", "13:30"),
            ("14:30", "16:30"),
            ("17:00", "19:00")
        ]

        today = date.today()
        new_slots_count = 0
        for s in services:
            for day_offset in range(0, 14):
                current_date = today + timedelta(days=day_offset)
                for start_t, end_t in slot_times:
                    exists = Slot.query.filter_by(
                        service_id=s.id,
                        slot_date=current_date,
                        start_time=start_t
                    ).first()
                    if not exists:
                        slot = Slot(
                            service_id=s.id,
                            slot_date=current_date,
                            start_time=start_t,
                            end_time=end_t,
                            capacity=1,
                            is_blocked=False
                        )
                        db.session.add(slot)
                        new_slots_count += 1
        db.session.commit()
        print(f"[Seed] Created {new_slots_count} slots across the next 14 days.")

if __name__ == '__main__':
    seed_database()
