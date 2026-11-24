import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.auth import (
    RegisterRequest, LoginRequest, UserOut, TokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest, RefreshRequest
)
from app.utils.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    create_password_reset_token, decode_token, check_rate_limit, sanitize_text
)
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: Request, body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    check_rate_limit(request, max_requests=10, window_seconds=60)
    
    clean_email = body.email.lower().strip()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    clean_name = sanitize_text(body.name)
    clean_phone = sanitize_text(body.phone)

    # New accounts start as "pending" (awaiting admin approval)
    new_user = User(
        name=clean_name,
        email=clean_email,
        phone=clean_phone,
        password_hash=hash_password(body.password),
        role=body.role,
        approval_status="pending",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log in-app welcome notification
    welcome_note = Notification(
        user_id=new_user.id,
        channel="in_app",
        type="welcome",
        title="Welcome to SpotMyShoot!",
        payload={"message": f"Welcome {new_user.name}! Your account has been registered and is pending admin verification."},
        status="sent",
        sent_at=datetime.datetime.utcnow()
    )
    db.add(welcome_note)
    db.commit()

    token_payload = {"sub": str(new_user.id), "role": new_user.role, "approval_status": new_user.approval_status}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    # Set httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=3600 * 24
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(new_user)
    )

@router.post("/login", response_model=TokenResponse)
def login(request: Request, body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    check_rate_limit(request, max_requests=15, window_seconds=60)
    
    clean_email = body.email.lower().strip()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated or suspended. Please contact support."
        )

    token_payload = {"sub": str(user.id), "role": user.role, "approval_status": user.approval_status}
    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=3600 * 24
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user)
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, body: RefreshRequest, response: Response, db: Session = Depends(get_db)):
    refresh_token = body.refresh_token or request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required.")

    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token type.")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

    token_payload = {"sub": str(user.id), "role": user.role, "approval_status": user.approval_status}
    new_access = create_access_token(token_payload)
    new_refresh = create_refresh_token(token_payload)

    response.set_cookie(
        key="access_token",
        value=new_access,
        httponly=True,
        samesite="lax",
        max_age=3600 * 24
    )

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=UserOut.model_validate(user)
    )

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully."}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)

@router.post("/forgot-password")
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    check_rate_limit(request, max_requests=5, window_seconds=60)
    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if user:
        reset_token = create_password_reset_token(user.email)
        # Store notification record
        note = Notification(
            user_id=user.id,
            channel="email",
            type="password_reset",
            title="SpotMyShoot Password Reset",
            payload={"reset_token": reset_token, "link": f"/forgot-password.html?token={reset_token}"},
            status="queued"
        )
        db.add(note)
        db.commit()
    # Always return 200 to prevent user enumeration
    return {"message": "If this email is registered, password reset instructions have been sent."}

@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.token)
    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token for password reset.")

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password has been successfully updated. You may now log in with your new password."}
