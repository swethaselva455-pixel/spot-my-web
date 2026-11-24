import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User
from app.utils.security import hash_password

def create_admin():
    db = SessionLocal()
    try:
        admin_email = "admin@spotmyshoot.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if admin:
            print(f"[INFO] Admin user {admin_email} already exists.")
            return

        new_admin = User(
            name="Super Admin",
            email=admin_email,
            phone="+919840198401",
            password_hash=hash_password("AdminPassword123!"),
            role="admin",
            approval_status="approved",
            is_active=True
        )
        db.add(new_admin)
        db.commit()
        print(f"[SUCCESS] Admin created: {admin_email} / AdminPassword123!")
    except Exception as e:
        print(f"[ERROR] Failed to create admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
