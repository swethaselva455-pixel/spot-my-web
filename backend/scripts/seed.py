import sys
import os
import datetime
from zoneinfo import ZoneInfo

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.property import Property, PropertyImage, PropertyCategory, AvailabilityRule, BlockedSlot
from app.models.booking import Booking
from app.models.payment import Payment, Refund
from app.models.review import Review
from app.models.notification import Notification
from app.utils.security import hash_password
from app.services.availability import ist_to_utc, IST

def seed_database():
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).filter(User.email == "admin@spotmyshoot.com").first():
            print("[INFO] Database already contains seed data.")
            return

        print("[SEED] Creating Admin...")
        default_pw = hash_password("Password123!")

        admin = User(
            name="SpotMyShoot Admin",
            email="admin@spotmyshoot.com",
            phone="+919840198401",
            password_hash=default_pw,
            role="admin",
            approval_status="approved",
            is_active=True
        )
        db.add(admin)

        print("[SEED] Creating 3 Owners...")
        owner1 = User(name="Karthik Raja", email="karthik.villas@spotmyshoot.com", phone="+919840111222", password_hash=default_pw, role="owner", approval_status="approved", is_active=True)
        owner2 = User(name="Priya Soundar", email="priya.studios@spotmyshoot.com", phone="+919840333444", password_hash=default_pw, role="owner", approval_status="approved", is_active=True)
        owner3 = User(name="Arun Natarajan", email="arun.estates@spotmyshoot.com", phone="+919840555666", password_hash=default_pw, role="owner", approval_status="pending", is_active=True)
        db.add_all([owner1, owner2, owner3])
        db.commit()

        print("[SEED] Creating 5 Customers...")
        cust1 = User(name="Ananya Sharma", email="ananya.lens@gmail.com", phone="+919840777888", password_hash=default_pw, role="customer", approval_status="approved", is_active=True)
        cust2 = User(name="Vikram Menon", email="vikram.reels@gmail.com", phone="+919840888999", password_hash=default_pw, role="customer", approval_status="approved", is_active=True)
        cust3 = User(name="Sneha Krishnan", email="sneha.shoots@gmail.com", phone="+919840999000", password_hash=default_pw, role="customer", approval_status="approved", is_active=True)
        cust4 = User(name="Rohit Verma", email="rohit.cinema@gmail.com", phone="+919840123456", password_hash=default_pw, role="customer", approval_status="approved", is_active=True)
        cust5 = User(name="Divya Balaji", email="divya.fashion@gmail.com", phone="+919840654321", password_hash=default_pw, role="customer", approval_status="pending", is_active=True)
        db.add_all([cust1, cust2, cust3, cust4, cust5])
        db.commit()

        print("[SEED] Creating 10 Properties across Chennai...")
        properties_data = [
            {
                "owner_id": owner1.id,
                "name": "The Azure Coastal Villa",
                "description": "Luxurious beachfront villa featuring infinity swimming pool, French colonial archways, sunset deck, and manicured green lawns right along the scenic ECR coast. Ideal for high-end fashion campaigns, pre-wedding romantic shoots, and cinematic music videos.",
                "city": "Chennai",
                "area": "ECR",
                "address": "4/12 Sea Cliff Conclave, Akkarai, ECR, Chennai - 600119",
                "latitude": 12.8984,
                "longitude": 80.2458,
                "property_type": "villa",
                "hourly_price": 4500,
                "min_hours": 3,
                "max_hours": 12,
                "max_crew_size": 35,
                "amenities": ["Air Conditioning", "Private Pool", "Dressing Rooms with Mirrors", "High-Speed WiFi", "Generator Power Backup", "Dedicated Parking for 10 Cars", "Kitchenette"],
                "rules_text": "No indoor smoke machines. Footwear allowed on wooden deck only. Music volume restricted after 10 PM.",
                "cancellation_policy": "flexible",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": False,
                "avg_rating": 4.9,
                "categories": ["Pre-wedding", "Fashion", "Cinematography", "Maternity"],
                "images": [
                    "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner2.id,
                "name": "Prism Studio Loft & Cyc Wall",
                "description": "Multi-set indoor creator studio equipped with a 30-foot seamless white cyclorama, RGB continuous godox lighting grid, textured terracotta backdrops, and modern aesthetic furniture for commercial reels and model portfolios.",
                "city": "Chennai",
                "area": "T. Nagar",
                "address": "78 G.N. Chetty Road, T. Nagar, Chennai - 600017",
                "latitude": 13.0418,
                "longitude": 80.2341,
                "property_type": "studio",
                "hourly_price": 2800,
                "min_hours": 2,
                "max_hours": 10,
                "max_crew_size": 20,
                "amenities": ["Infinite Cyclorama Wall", "Studio Strobe Lights", "Air Conditioning", "Vanity Makeup Stations", "Client Lounge", "Steamer & Ironing Board", "Sound Dampening"],
                "rules_text": "Keep cyclorama clean. Repainting fee applies if shoe marks exceed normal wear. Strictly no glitter without prior consent.",
                "cancellation_policy": "moderate",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": True,
                "avg_rating": 4.8,
                "categories": ["Reels", "Fashion", "Cinematography"],
                "images": [
                    "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner1.id,
                "name": "The Palms Secret Botanical Garden",
                "description": "A secluded 2-acre private botanical oasis filled with towering royal palms, exotic ferns, cobblestone pathways, rustic glass greenhouse, and marble fountains.",
                "city": "Chennai",
                "area": "Adyar",
                "address": "15 Greenways Enclave, Adyar, Chennai - 600020",
                "latitude": 13.0067,
                "longitude": 80.2575,
                "property_type": "garden",
                "hourly_price": 3200,
                "min_hours": 2,
                "max_hours": 8,
                "max_crew_size": 30,
                "amenities": ["Lush Landscaping", "Glass Greenhouse", "Changing Tent", "Restrooms", "Free Valet Parking", "Natural Sunlight Pergola"],
                "rules_text": "Do not pluck flowers or disturb water features. Drones permitted with caution around trees.",
                "cancellation_policy": "flexible",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": False,
                "avg_rating": 4.7,
                "categories": ["Maternity", "Pre-wedding", "Wedding"],
                "images": [
                    "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1596241913242-eb4e0f49bf69?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner2.id,
                "name": "Baywatch Private Beachfront Deck",
                "description": "Private beach pavilion with uninterrupted panoramic views of the Bay of Bengal, golden sand frontage, wooden boardwalk, and nautical boho cabanas.",
                "city": "Chennai",
                "area": "ECR",
                "address": "22 Coastal Road, Kovalam, ECR, Chennai - 603112",
                "latitude": 12.7915,
                "longitude": 80.2520,
                "property_type": "beach",
                "hourly_price": 4000,
                "min_hours": 3,
                "max_hours": 12,
                "max_crew_size": 40,
                "amenities": ["Direct Beach Access", "Boho Cabanas", "Outdoor Showers", "Air Conditioned Green Room", "Security Guards", "Barbecue Grill"],
                "rules_text": "Do not swim in rough surf. Keep trash sorted. Bonfires require prior permission.",
                "cancellation_policy": "strict",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": False,
                "avg_rating": 4.9,
                "categories": ["Pre-wedding", "Fashion", "Cinematography", "Reels"],
                "images": [
                    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner1.id,
                "name": "Chettinad Heritage Mansion Courtyard",
                "description": "Authentic 19th-century Chettinad architectural mansion boasting Burmese teak pillars, Belgian glass chandeliers, ornate Athangudi handmade tiles, and a sunlit inner open courtyard.",
                "city": "Chennai",
                "area": "Adyar",
                "address": "8 Kasturibai Nagar 3rd Cross, Adyar, Chennai - 600020",
                "latitude": 13.0033,
                "longitude": 80.2530,
                "property_type": "heritage",
                "hourly_price": 5500,
                "min_hours": 4,
                "max_hours": 12,
                "max_crew_size": 45,
                "amenities": ["Teak Wood Pillar Courtyard", "Antique Heritage Furniture", "Dressing Suite", "Full Air Conditioning", "Modern Restrooms", "Valet Parking"],
                "rules_text": "Treat heritage relics with respect. No heavy c-stands without rubber boots on Athangudi tiles.",
                "cancellation_policy": "strict",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": False,
                "avg_rating": 5.0,
                "categories": ["Wedding", "Pre-wedding", "Fashion", "Cinematography"],
                "images": [
                    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner2.id,
                "name": "Neon Urban Rooftop & Penthouse",
                "description": "Ultra-sleek tech corridor penthouse featuring floor-to-ceiling glass panoramic city vistas, infinity glass balcony, exposed concrete walls, and vibrant neon accents.",
                "city": "Chennai",
                "area": "OMR",
                "address": "Level 18, Cyber Heights, Navalur, OMR, Chennai - 603103",
                "latitude": 12.8468,
                "longitude": 80.2268,
                "property_type": "studio",
                "hourly_price": 3000,
                "min_hours": 2,
                "max_hours": 8,
                "max_crew_size": 20,
                "amenities": ["City Skyline View", "Custom Neon Installations", "DJ Sound System", "Air Conditioning", "Elevator Freight Access", "Bar Counter"],
                "rules_text": "Keep balcony glass clean. Strictly no jumping near perimeter glass barriers.",
                "cancellation_policy": "moderate",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": True,
                "avg_rating": 4.6,
                "categories": ["Reels", "Fashion", "Cinematography"],
                "images": [
                    "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner1.id,
                "name": "The Willow Creek Lawn & Lakeview Villa",
                "description": "Quiet lake-adjacent villa in Velachery surrounded by weeping willows, floating wooden jetty, glass tea house, and fairy lit evening garden.",
                "city": "Chennai",
                "area": "Velachery",
                "address": "45 Lakeview Avenue, Velachery, Chennai - 600042",
                "latitude": 12.9815,
                "longitude": 80.2180,
                "property_type": "villa",
                "hourly_price": 3800,
                "min_hours": 3,
                "max_hours": 10,
                "max_crew_size": 30,
                "amenities": ["Lakefront Jetty", "Fairy Light Canopies", "Glass Conservatory", "Air Conditioned Lounge", "Changing Room", "Parking for 8 Cars"],
                "rules_text": "Life jackets required when on jetty. Do not discard plastic near the lake.",
                "cancellation_policy": "moderate",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": False,
                "avg_rating": 4.8,
                "categories": ["Maternity", "Pre-wedding", "Reels"],
                "images": [
                    "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1512915922686-57c11dde9b6b?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner2.id,
                "name": "Industrial Warehouse Creative Lab",
                "description": "Raw 4,000 sq ft industrial hangar featuring distressed brick walls, high corrugated metal ceilings, rusted iron staircases, and polished concrete floors.",
                "city": "Chennai",
                "area": "OMR",
                "address": "Plot 12, Industrial Estate, Thoraipakkam, OMR, Chennai - 600097",
                "latitude": 12.9360,
                "longitude": 80.2300,
                "property_type": "studio",
                "hourly_price": 2500,
                "min_hours": 3,
                "max_hours": 14,
                "max_crew_size": 50,
                "amenities": ["3-Phase High Voltage Power", "Drive-in Vehicle Ramp", "Scaffolding Rigs", "High Ceilings (24ft)", "Industrial Fans", "Restrooms"],
                "rules_text": "Vehicles must place oil drip pans on concrete floor. Rigging requires certified grip personnel.",
                "cancellation_policy": "flexible",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": True,
                "avg_rating": 4.5,
                "categories": ["Cinematography", "Fashion", "Reels"],
                "images": [
                    "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1200&q=80",
                    "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner3.id,
                "name": "Serenade Glass House Villa",
                "description": "Minimalist Scandinavian all-glass villa with warm oak flooring, open concept kitchen studio, indoor ficus tree, and filtered northern skylights.",
                "city": "Chennai",
                "area": "ECR",
                "address": "7 Neelankarai Beach Road, ECR, Chennai - 600115",
                "latitude": 12.9485,
                "longitude": 80.2580,
                "property_type": "villa",
                "hourly_price": 4200,
                "min_hours": 3,
                "max_hours": 10,
                "max_crew_size": 25,
                "amenities": ["Skylight Natural Illumination", "Nordic Kitchen Set", "Central AC", "Designer Furniture", "Covered Carport"],
                "rules_text": "No outdoor shoes inside glass house. Protective socks provided.",
                "cancellation_policy": "moderate",
                "approval_status": "pending", # Awaiting admin review!
                "is_published": False,
                "auto_accept": False,
                "avg_rating": 0.0,
                "categories": ["Maternity", "Fashion", "Reels"],
                "images": [
                    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80"
                ]
            },
            {
                "owner_id": owner3.id,
                "name": "The Vintage Colonial Courtyard",
                "description": "Picturesque Portuguese-influenced garden villa in Velachery with pastel yellow walls, terracotta roof shingles, and wrought iron balconies.",
                "city": "Chennai",
                "area": "Velachery",
                "address": "19 Gandhi Salai, Velachery, Chennai - 600042",
                "latitude": 12.9780,
                "longitude": 80.2195,
                "property_type": "heritage",
                "hourly_price": 3500,
                "min_hours": 2,
                "max_hours": 8,
                "max_crew_size": 25,
                "amenities": ["Vintage Balconies", "Garden Courtyard", "Restrooms", "Air Conditioned Lounge", "Parking"],
                "rules_text": "Do not lean over antique wooden railings.",
                "cancellation_policy": "flexible",
                "approval_status": "approved",
                "is_published": True,
                "auto_accept": False,
                "avg_rating": 4.6,
                "categories": ["Pre-wedding", "Maternity", "Wedding"],
                "images": [
                    "https://images.unsplash.com/photo-1544984243-ec57ea16fe25?auto=format&fit=crop&w=1200&q=80"
                ]
            }
        ]

        properties = []
        for pdata in properties_data:
            cats = pdata.pop("categories")
            imgs = pdata.pop("images")
            prop = Property(**pdata)
            db.add(prop)
            db.commit()
            db.refresh(prop)

            for c in cats:
                db.add(PropertyCategory(property_id=prop.id, category=c))

            for idx, img_url in enumerate(imgs):
                db.add(PropertyImage(property_id=prop.id, url=img_url, is_cover=(idx == 0), sort_order=idx))

            for day in range(7):
                db.add(AvailabilityRule(
                    property_id=prop.id,
                    day_of_week=day,
                    open_time=datetime.time(6, 0),
                    close_time=datetime.time(22, 0)
                ))

            properties.append(prop)

        db.commit()

        print("[SEED] Creating realistic bookings across statuses...")
        now_utc = datetime.datetime.utcnow()

        # 1. Confirmed shoot tomorrow for Ananya
        tomorrow_start = now_utc + datetime.timedelta(days=1, hours=2)
        tomorrow_end = tomorrow_start + datetime.timedelta(hours=4)
        sub1 = properties[0].hourly_price * 4
        gst1 = int(round(sub1 * 0.18))
        fee1 = int(round(sub1 * 0.10))
        b1 = Booking(
            booking_code="#SMS-1082",
            property_id=properties[0].id,
            customer_id=cust1.id,
            shoot_category="Pre-wedding",
            start_datetime=tomorrow_start,
            end_datetime=tomorrow_end,
            duration_hours=4,
            crew_size=8,
            special_requests="Requesting 2 wardrobe changes and drone landing clearance.",
            subtotal=sub1,
            gst_amount=gst1,
            platform_fee=fee1,
            total_amount=sub1 + gst1 + fee1,
            status="confirmed",
            created_at=now_utc - datetime.timedelta(days=2)
        )
        db.add(b1)
        db.commit()
        db.refresh(b1)

        p1 = Payment(
            booking_id=b1.id,
            razorpay_order_id="order_seed_rzp_1082",
            razorpay_payment_id="pay_seed_rzp_1082",
            razorpay_signature="mock_signature_success",
            amount=b1.total_amount,
            status="captured",
            method="upi"
        )
        db.add(p1)

        # 2. Completed shoot with 5-star review
        past_start = now_utc - datetime.timedelta(days=5, hours=6)
        past_end = past_start + datetime.timedelta(hours=3)
        sub2 = properties[1].hourly_price * 3
        gst2 = int(round(sub2 * 0.18))
        fee2 = int(round(sub2 * 0.10))
        b2 = Booking(
            booking_code="#SMS-1045",
            property_id=properties[1].id,
            customer_id=cust2.id,
            shoot_category="Fashion",
            start_datetime=past_start,
            end_datetime=past_end,
            duration_hours=3,
            crew_size=6,
            special_requests="Need extra C-stands and warm lighting grid setup.",
            subtotal=sub2,
            gst_amount=gst2,
            platform_fee=fee2,
            total_amount=sub2 + gst2 + fee2,
            status="completed",
            created_at=now_utc - datetime.timedelta(days=7)
        )
        db.add(b2)
        db.commit()
        db.refresh(b2)

        rev2 = Review(
            booking_id=b2.id,
            property_id=properties[1].id,
            customer_id=cust2.id,
            rating=5,
            comment="The cyclorama wall was in flawless pristine condition. AC and makeup mirrors made our 3-hour fashion shoot super smooth and productive!"
        )
        db.add(rev2)

        # 3. Pending owner acceptance (paid)
        next_week = now_utc + datetime.timedelta(days=4)
        sub3 = properties[2].hourly_price * 3
        gst3 = int(round(sub3 * 0.18))
        fee3 = int(round(sub3 * 0.10))
        b3 = Booking(
            booking_code="#SMS-1090",
            property_id=properties[2].id,
            customer_id=cust3.id,
            shoot_category="Maternity",
            start_datetime=next_week,
            end_datetime=next_week + datetime.timedelta(hours=3),
            duration_hours=3,
            crew_size=4,
            special_requests="Requesting botanical greenhouse access for maternity portraits.",
            subtotal=sub3,
            gst_amount=gst3,
            platform_fee=fee3,
            total_amount=sub3 + gst3 + fee3,
            status="pending_owner",
            created_at=now_utc - datetime.timedelta(hours=2)
        )
        db.add(b3)
        db.commit()
        db.refresh(b3)

        p3 = Payment(
            booking_id=b3.id,
            razorpay_order_id="order_seed_rzp_1090",
            razorpay_payment_id="pay_seed_rzp_1090",
            razorpay_signature="mock_signature_success",
            amount=b3.total_amount,
            status="captured",
            method="card"
        )
        db.add(p3)

        # 4. Active temporary hold (expires in 8 mins)
        in_3_days = now_utc + datetime.timedelta(days=3)
        sub4 = properties[3].hourly_price * 4
        gst4 = int(round(sub4 * 0.18))
        fee4 = int(round(sub4 * 0.10))
        b4 = Booking(
            booking_code="#SMS-1102",
            property_id=properties[3].id,
            customer_id=cust4.id,
            shoot_category="Cinematography",
            start_datetime=in_3_days,
            end_datetime=in_3_days + datetime.timedelta(hours=4),
            duration_hours=4,
            crew_size=12,
            subtotal=sub4,
            gst_amount=gst4,
            platform_fee=fee4,
            total_amount=sub4 + gst4 + fee4,
            status="hold",
            hold_expires_at=now_utc + datetime.timedelta(minutes=8),
            created_at=now_utc - datetime.timedelta(minutes=2)
        )
        db.add(b4)

        # 5. Cancelled with refund record
        b5 = Booking(
            booking_code="#SMS-1011",
            property_id=properties[0].id,
            customer_id=cust1.id,
            shoot_category="Reels",
            start_datetime=now_utc + datetime.timedelta(days=8),
            end_datetime=now_utc + datetime.timedelta(days=8, hours=2),
            duration_hours=2,
            crew_size=3,
            subtotal=9000,
            gst_amount=1620,
            platform_fee=900,
            total_amount=11520,
            status="cancelled_by_customer",
            cancellation_reason="Creator rescheduled shoot date due to client availability.",
            created_at=now_utc - datetime.timedelta(days=10)
        )
        db.add(b5)
        db.commit()
        db.refresh(b5)

        p5 = Payment(
            booking_id=b5.id,
            razorpay_order_id="order_seed_rzp_1011",
            razorpay_payment_id="pay_seed_rzp_1011",
            amount=11520,
            status="refunded",
            method="netbanking"
        )
        db.add(p5)
        db.commit()

        rf5 = Refund(
            payment_id=p5.id,
            booking_id=b5.id,
            amount=10620, # subtotal + GST refunded under flexible policy > 24h
            razorpay_refund_id="rfnd_seed_rzp_1011",
            status="processed",
            reason="Flexible cancellation > 24h prior to shoot"
        )
        db.add(rf5)

        # In-app notifications
        n1 = Notification(
            user_id=cust1.id,
            booking_id=b1.id,
            channel="in_app",
            type="booking_confirmed",
            title=f"Booking Confirmed: {b1.booking_code}",
            payload={"message": f"Your shoot at {properties[0].name} has been confirmed for tomorrow!"},
            status="sent",
            sent_at=now_utc
        )
        n2 = Notification(
            user_id=owner1.id,
            booking_id=b1.id,
            channel="in_app",
            type="booking_request",
            title=f"Shoot Tomorrow: {b1.booking_code}",
            payload={"message": f"Reminder: Ananya has a confirmed shoot tomorrow at {properties[0].name}."},
            status="sent",
            sent_at=now_utc
        )
        n3 = Notification(
            user_id=owner1.id,
            booking_id=b3.id,
            channel="in_app",
            type="booking_request",
            title=f"New Booking Request: {b3.booking_code}",
            payload={"message": f"Sneha requested {properties[2].name} for Maternity shoot."},
            status="queued",
            sent_at=now_utc
        )
        db.add_all([n1, n2, n3])
        db.commit()

        print("[SUCCESS] Seeding completed successfully!")
        print("  - 1 Admin: admin@spotmyshoot.com / Password123!")
        print("  - 3 Owners: karthik.villas@spotmyshoot.com, priya.studios@spotmyshoot.com, arun.estates@spotmyshoot.com")
        print("  - 5 Customers: ananya.lens@gmail.com, vikram.reels@gmail.com, sneha.shoots@gmail.com, rohit.cinema@gmail.com, divya.fashion@gmail.com")
        print("  - 10 Properties across Chennai (ECR, T. Nagar, Adyar, OMR, Velachery)")
        print("  - 5 Bookings across confirmed, completed, pending_owner, hold, cancelled")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
