import pytest
import os
import sys

# Ensure backend root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.property import Property, PropertyCategory, AvailabilityRule
from app.utils.security import hash_password, create_access_token

TEST_DB_URL = "sqlite:///./test_spotmyshoot.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_spotmyshoot.db"):
        try:
            os.remove("./test_spotmyshoot.db")
        except Exception:
            pass

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_admin(db_session):
    admin = db_session.query(User).filter(User.email == "testadmin@spotmyshoot.com").first()
    if not admin:
        admin = User(
            name="Test Admin",
            email="testadmin@spotmyshoot.com",
            phone="+919840111111",
            password_hash=hash_password("Pass123!"),
            role="admin",
            approval_status="approved",
            is_active=True
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    return admin

@pytest.fixture
def test_owner(db_session):
    owner = db_session.query(User).filter(User.email == "testowner@spotmyshoot.com").first()
    if not owner:
        owner = User(
            name="Test Owner",
            email="testowner@spotmyshoot.com",
            phone="+919840222222",
            password_hash=hash_password("Pass123!"),
            role="owner",
            approval_status="approved",
            is_active=True
        )
        db_session.add(owner)
        db_session.commit()
        db_session.refresh(owner)
    return owner

@pytest.fixture
def test_customer(db_session):
    cust = db_session.query(User).filter(User.email == "testcust@spotmyshoot.com").first()
    if not cust:
        cust = User(
            name="Test Customer",
            email="testcust@spotmyshoot.com",
            phone="+919840333333",
            password_hash=hash_password("Pass123!"),
            role="customer",
            approval_status="approved",
            is_active=True
        )
        db_session.add(cust)
        db_session.commit()
        db_session.refresh(cust)
    return cust

@pytest.fixture
def customer_headers(test_customer):
    token = create_access_token({"sub": str(test_customer.id), "role": test_customer.role, "approval_status": test_customer.approval_status})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def owner_headers(test_owner):
    token = create_access_token({"sub": str(test_owner.id), "role": test_owner.role, "approval_status": test_owner.approval_status})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_headers(test_admin):
    token = create_access_token({"sub": str(test_admin.id), "role": test_admin.role, "approval_status": test_admin.approval_status})
    return {"Authorization": f"Bearer {token}"}
