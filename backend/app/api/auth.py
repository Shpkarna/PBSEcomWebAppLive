"""Authentication API routes."""
from fastapi import APIRouter, HTTPException, status, Depends, Response, Cookie, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from app.database import get_collection
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, UserProfileUpdate
from app.schemas.user_schemas import (
    OTPSendRequest, OTPVerifyRegisterRequest, ChangePhoneRequest,
    ChangePhoneVerifyRequest, EmailVerificationRequest
)
from app.utils.security import (
    hash_password, verify_password, create_access_token,
    decode_token, get_token_from_credentials, security,
)
from app.utils.logger import log_event
from app.config import settings
from app.api.session_utils import (
    get_or_create_session, validate_session, store_token_in_session,
    get_existing_token, invalidate_sessions_for_device,
)
from app.utils.id_generator import next_customer_id
from app.services.otp_service import OTPService
import uuid
import re

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _get_authenticated_username(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Resolve username from bearer token."""
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload["sub"]


def _is_mobile_otp_enabled() -> bool:
    return bool(settings.enable_mobile_otp_verification)


def _is_email_verification_enabled() -> bool:
    return bool(settings.enable_email_verification)


def _validate_strong_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must include at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must include at least one lowercase letter")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must include at least one number")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must include at least one special character")


def _initiate_email_verification(username: str, email: str, path: str, trigger: str):
    verification_token = str(uuid.uuid4())
    verification_records = get_collection("email_verifications")

    verification_records.delete_many({
        "username": username,
        "verified": False,
        "expires_at": {"$gt": datetime.utcnow()},
    })

    verification_records.insert_one({
        "username": username,
        "email": email,
        "token": verification_token,
        "verified": False,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=24),
    })

    log_event(
        "email_verification_initiated",
        user=username,
        details={"email": email, "trigger": trigger},
        path=path,
    )

    return verification_token


@router.get("/mobile-otp-config")
async def get_mobile_otp_config():
    """Expose whether mobile OTP verification is enabled for UI behavior."""
    return {"enable_mobile_otp_verification": _is_mobile_otp_enabled()}


@router.get("/email-verification-config")
async def get_email_verification_config():
    """Expose whether email verification is enabled for UI behavior."""
    return {"enable_email_verification": _is_email_verification_enabled()}


@router.post("/register/send-otp")
async def register_send_otp(request: OTPSendRequest):
    """
    Step 1: Send OTP to phone number during registration.
    User provides registration details, system validates and sends OTP to phone.
    """
    users_col = get_collection("users")
    _validate_strong_password(request.password)
    if not _is_mobile_otp_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile OTP verification is disabled by company configuration.",
        )
    
    # Validate that username and email are not already taken
    if request.username == settings.admin_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username 'admin' is reserved for administrators only")
    
    if users_col.find_one({"$or": [{"username": request.username}, {"email": request.email}]}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username or email already registered")
    
    # Create OTP record and send OTP to phone
    result = OTPService.create_otp_record(phone=request.phone, purpose="registration")
    if not result.get("otp_sent", False):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send OTP to phone. Please verify SMS provider settings and try again.",
        )
    
    log_event("registration_otp_sent", user=request.username, 
             details={"email": request.email, "phone": request.phone}, 
             path="/api/auth/register/send-otp")
    
    return {
        "message": result["message"],
        "expires_at": result["expires_at"],
        "phone": request.phone,
    }


@router.post("/register/verify-otp")
async def register_verify_otp(request: OTPVerifyRegisterRequest):
    """
    Step 2: Verify OTP and complete registration.
    User received OTP on phone, provides it here, and account is created WITHOUT customer role.
    Admin will assign customer role after verification.
    """
    users_col = get_collection("users")
    _validate_strong_password(request.password)
    if not _is_mobile_otp_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile OTP verification is disabled by company configuration.",
        )
    
    # Verify OTP
    verification_result = OTPService.verify_otp(phone=request.phone, otp=request.otp, purpose="registration")
    
    if not verification_result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=verification_result["message"])
    
    # Check again that username/email not taken (in case of race condition)
    if users_col.find_one({"$or": [{"username": request.username}, {"email": request.email}]}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username or email already registered")
    
    # Create user WITHOUT customer role (NO ROLE ASSIGNED YET)
    user_dict = {
        "username": request.username,
        "email": request.email,
        "password_hash": hash_password(request.password),
        "full_name": request.full_name,
        "phone": request.phone,
        "dob": request.dob,
        "customer_id": next_customer_id(),
        "role": "user",
        "is_active": True,
        "phone_verified": True,  # Phone verified via OTP
        "email_verified": False,  # Email not yet verified
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    result = users_col.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id

    email_verification_pending = False
    verification_token = None
    if _is_email_verification_enabled():
        verification_token = _initiate_email_verification(
            username=request.username,
            email=request.email,
            path="/api/auth/register/verify-otp",
            trigger="registration",
        )
        email_verification_pending = True
    
    # Mark OTP record as used
    OTPService.mark_otp_used(verification_result["otp_record_id"])
    
    log_event("user_registered", user=request.username, 
             details={"email": request.email, "phone": request.phone, "phone_verified": True},
             path="/api/auth/register/verify-otp")
    
    return {
        "message": "Registration successful. Please verify your email to complete account verification." if email_verification_pending else "Registration successful.",
        "user": {
            "id": str(user_dict["_id"]),
            "username": user_dict["username"],
            "email": user_dict["email"],
            "full_name": user_dict["full_name"],
            "phone": user_dict["phone"],
            "phone_verified": True,
            "role": user_dict["role"],
        },
        "email_verification_pending": email_verification_pending,
        "verification_token": verification_token,
    }


@router.post("/register")
async def register(user: UserCreate):
    """
    Registration endpoint.
    - When mobile OTP verification is enabled: caller must use send-otp/verify-otp flow.
    - When disabled: direct registration is allowed.
    """
    if _is_mobile_otp_enabled():
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail="Registration endpoint deprecated. Use /register/send-otp and /register/verify-otp instead.")

    _validate_strong_password(user.password)

    users_col = get_collection("users")
    if user.username == settings.admin_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username 'admin' is reserved for administrators only")

    if users_col.find_one({"$or": [{"username": user.username}, {"email": user.email}]}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username or email already registered")

    user_dict = {
        "username": user.username,
        "email": user.email,
        "password_hash": hash_password(user.password),
        "full_name": user.full_name,
        "phone": user.phone,
        "dob": user.dob,
        "customer_id": next_customer_id(),
        "role": "user",
        "is_active": True,
        "phone_verified": False,
        "email_verified": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = users_col.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id

    email_verification_pending = False
    verification_token = None
    if _is_email_verification_enabled():
        verification_token = _initiate_email_verification(
            username=user.username,
            email=user.email,
            path="/api/auth/register",
            trigger="registration",
        )
        email_verification_pending = True

    log_event("user_registered", user=user.username,
              details={"email": user.email, "phone": user.phone, "phone_verified": False, "otp_enabled": False},
              path="/api/auth/register")

    return {
        "message": "Registration successful. Please verify your email to complete account verification." if email_verification_pending else "Registration successful.",
        "user": {
            "id": str(user_dict["_id"]),
            "username": user_dict["username"],
            "email": user_dict["email"],
            "full_name": user_dict["full_name"],
            "phone": user_dict["phone"],
            "phone_verified": False,
            "role": user_dict["role"],
        },
        "email_verification_pending": email_verification_pending,
        "verification_token": verification_token,
    }


@router.post("/login")
async def login(user_credentials: UserLogin, request: Request, response: Response):
    """User login.

    Session & token rules
    ---------------------
    * For a given (client_ip, client_mac) only **one** session is valid.
    * Within that session a JWT is created **only** if no active (non-expired)
      token has been issued.  If one exists the same token is returned.
    """
    users_col = get_collection("users")
    log_event("login_attempt", user=user_credentials.username, path="/api/auth/login")
    user = users_col.find_one({"username": user_credentials.username})
    if not user or not verify_password(user_credentials.password, user.get("password_hash", "")):
        log_event("login_failed", user=user_credentials.username,
                  details={"reason": "invalid credentials"}, path="/api/auth/login")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.get("is_active", True):
        log_event("login_failed", user=user_credentials.username,
                  details={"reason": "inactive account"}, path="/api/auth/login")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    # --- Resolve device identity (IP + MAC) ---
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.client.host
        if request.client else "unknown"
    )
    client_mac = request.headers.get("X-Client-MAC", "unknown")

    # --- Session: one per (IP, MAC) with token reuse ---
    session_token, reused = get_or_create_session(
        username=user["username"],
        client_ip=client_ip,
        client_mac=client_mac,
    )

    if reused:
        # Session is alive and a valid token was already issued – return it.
        access_token = get_existing_token(session_token)
    else:
        # Mint a new JWT and persist it inside the session document.
        token_expiry_delta = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user["username"], "role": user.get("role", "customer"), "sid": session_token},
            expires_delta=token_expiry_delta,
        )
        token_expires_at = datetime.utcnow() + token_expiry_delta
        store_token_in_session(session_token, access_token, token_expires_at)

    response.set_cookie(key=settings.session_cookie_name, value=session_token,
                        httponly=True, samesite="lax", max_age=settings.session_expire_minutes * 60)
    user_model = UserResponse(**{**user, "_id": str(user["_id"])})
    log_event("login", user=user["username"],
             details={"client_ip": client_ip, "client_mac": client_mac,
                      "session_reused": reused, "session_id": session_token},
             path="/api/auth/login")
    return {"access_token": access_token, "token_type": "bearer", "user": user_model}


@router.post("/logout")
async def logout(response: Response, session_id: str = Cookie(None)):
    """Logout user – invalidates the session and its stored token."""
    if session_id:
        sessions_col = get_collection("sessions")
        session = sessions_col.find_one({"_id": session_id})
        username = session["username"] if session else session_id
        sessions_col.delete_one({"_id": session_id})
        response.delete_cookie(settings.session_cookie_name)
        log_event("logout", user=username, path="/api/auth/logout")
        return {"message": "Logged out"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active session")


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session_id: str = Cookie(None),
):
    """Get current user information"""
    username = None
    if credentials:
        token = get_token_from_credentials(credentials)
        payload = decode_token(token)
        if payload:
            username = payload.get("sub")
    if not username and session_id:
        username = validate_session(session_id)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or missing authentication")
    user = get_collection("users").find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(**{**user, "_id": str(user["_id"])})


@router.get("/profile")
async def get_profile(current_username: str = Depends(_get_authenticated_username)):
    """Get full profile details for current user."""
    user = get_collection("users").find_one({"username": current_username}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return {
        "id": str(user.get("_id")),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "full_name": user.get("full_name"),
        "phone": user.get("phone"),
        "dob": user.get("dob"),
        "sex": user.get("sex"),
        "marital_status": user.get("marital_status"),
        "address": user.get("address"),
        "address_data": user.get("address_data", {}),
        "saved_payment_data": user.get("saved_payment_data", {}),
        "phone_verified": user.get("phone_verified", False),
        "email_verified": user.get("email_verified", False),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }


@router.put("/profile")
async def update_profile(
    profile_data: UserProfileUpdate,
    current_username: str = Depends(_get_authenticated_username),
):
    """Update current user's profile data."""
    users_col = get_collection("users")
    user = users_col.find_one({"username": current_username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updates = {k: v for k, v in profile_data.model_dump().items() if v is not None}
    email_verification_pending = False

    requested_email = updates.get("email")
    if requested_email and requested_email != user.get("email"):
        existing_with_email = users_col.find_one({"email": requested_email, "username": {"$ne": current_username}})
        if existing_with_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already used by another user")

        updates["email_verified"] = False
        if _is_email_verification_enabled():
            _initiate_email_verification(
                username=current_username,
                email=requested_email,
                path="/api/auth/profile",
                trigger="profile_email_change",
            )
            email_verification_pending = True

        log_event(
            "profile_email_changed_pending_verification",
            user=current_username,
            details={"email": requested_email, "email_verification_pending": email_verification_pending},
            path="/api/auth/profile",
        )

    updates["updated_at"] = datetime.utcnow()
    users_col.update_one({"username": current_username}, {"$set": updates})

    updated = users_col.find_one({"username": current_username}, {"password_hash": 0})
    return {
        "message": "Profile updated successfully. Please verify your new email address." if email_verification_pending else "Profile updated successfully",
        "email_verification_pending": email_verification_pending,
        "profile": {
            "id": str(updated.get("_id")),
            "username": updated.get("username"),
            "email": updated.get("email"),
            "role": updated.get("role"),
            "full_name": updated.get("full_name"),
            "phone": updated.get("phone"),
            "dob": updated.get("dob"),
            "sex": updated.get("sex"),
            "marital_status": updated.get("marital_status"),
            "address": updated.get("address"),
            "address_data": updated.get("address_data", {}),
            "saved_payment_data": updated.get("saved_payment_data", {}),
            "phone_verified": updated.get("phone_verified", False),
            "email_verified": updated.get("email_verified", False),
            "created_at": updated.get("created_at"),
            "updated_at": updated.get("updated_at"),
        },
    }


@router.post("/verify-email/send")
async def send_email_verification(
    request: EmailVerificationRequest,
    current_username: str = Depends(_get_authenticated_username),
):
    """
    Send email verification link to user's email (optional process).
    In production, this would send an actual email with a verification link.
    """
    users_col = get_collection("users")
    if not _is_email_verification_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification is disabled by company configuration.",
        )

    user = users_col.find_one({"username": current_username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Verify email matches user's email
    if request.email != user.get("email"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Email does not match user's registered email")
    
    verification_token = _initiate_email_verification(
        username=current_username,
        email=request.email,
        path="/api/auth/verify-email/send",
        trigger="manual",
    )
    
    return {
        "message": "Email verification link sent (in production, check your email)",
        "verification_token": verification_token,  # For testing purposes
        "email": request.email,
    }


@router.post("/verify-email/confirm")
async def confirm_email_verification(
    token: str,
    current_username: str = Depends(_get_authenticated_username),
):
    """Confirm email verification with token."""
    users_col = get_collection("users")
    verification_records = get_collection("email_verifications")
    
    user = users_col.find_one({"username": current_username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Verify token
    verification_record = verification_records.find_one({
        "username": current_username,
        "token": token,
        "verified": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not verification_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid or expired verification token")
    
    # Mark email as verified
    users_col.update_one(
        {"username": current_username},
        {"$set": {"email_verified": True, "updated_at": datetime.utcnow()}}
    )
    
    verification_records.update_one(
        {"_id": verification_record["_id"]},
        {"$set": {"verified": True, "verified_at": datetime.utcnow()}}
    )
    
    log_event("email_verified", user=current_username, path="/api/auth/verify-email/confirm")
    
    return {"message": "Email verified successfully"}


@router.post("/change-phone/send-otp")
async def change_phone_send_otp(
    request: ChangePhoneRequest,
    current_username: str = Depends(_get_authenticated_username),
):
    """
    Step 1: Send OTP to new phone number for phone change request.
    """
    users_col = get_collection("users")
    if not _is_mobile_otp_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile OTP verification is disabled by company configuration.",
        )
    user = users_col.find_one({"username": current_username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Check if new phone is already registered by another user
    if users_col.find_one({"phone": request.new_phone, "username": {"$ne": current_username}}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Phone number already registered by another user")
    
    # Create OTP record for phone change
    result = OTPService.create_otp_record(phone=request.new_phone, purpose="phone_change")
    
    log_event("phone_change_otp_sent", user=current_username,
             details={"new_phone": request.new_phone}, path="/api/auth/change-phone/send-otp")
    
    return {
        "message": result["message"],
        "expires_at": result["expires_at"],
        "phone": request.new_phone,
    }


@router.post("/change-phone/verify-otp")
async def change_phone_verify_otp(
    request: ChangePhoneVerifyRequest,
    current_username: str = Depends(_get_authenticated_username),
):
    """
    Step 2: Verify OTP and update phone number.
    """
    users_col = get_collection("users")
    if not _is_mobile_otp_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mobile OTP verification is disabled by company configuration.",
        )
    user = users_col.find_one({"username": current_username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Verify OTP
    verification_result = OTPService.verify_otp(
        phone=request.new_phone, otp=request.otp, purpose="phone_change"
    )
    
    if not verification_result["success"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=verification_result["message"])
    
    # Check again that new phone is not taken by another user
    if users_col.find_one({"phone": request.new_phone, "username": {"$ne": current_username}}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Phone number already registered by another user")
    
    # Update phone number
    old_phone = user.get("phone")
    users_col.update_one(
        {"username": current_username},
        {"$set": {
            "phone": request.new_phone,
            "phone_verified": True,
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Mark OTP as used
    OTPService.mark_otp_used(verification_result["otp_record_id"])
    
    log_event("phone_number_changed", user=current_username,
             details={"old_phone": old_phone, "new_phone": request.new_phone},
             path="/api/auth/change-phone/verify-otp")
    
    return {"message": "Phone number updated successfully"}


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


@router.put("/change-password")
async def change_password(
    req: PasswordChangeRequest,
    current_username: str = Depends(_get_authenticated_username),
):
    """Change the authenticated user's password."""
    users_col = get_collection("users")
    _validate_strong_password(req.new_password)
    user = users_col.find_one({"username": current_username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(req.current_password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    users_col.update_one(
        {"username": current_username},
        {"$set": {"password_hash": hash_password(req.new_password), "updated_at": datetime.utcnow()}},
    )
    log_event("password_change", user=current_username, path="/api/auth/change-password")
    return {"message": "Password changed successfully"}
