"""User-related Pydantic schemas."""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from app.schemas import PyObjectId


class AddressData(BaseModel):
    street1: Optional[str] = None
    street2: Optional[str] = None
    landmark: Optional[str] = None
    district: Optional[str] = None
    area: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None


class SavedPaymentData(BaseModel):
    card_holder: Optional[str] = None
    card_last4: Optional[str] = None
    card_brand: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    upi_id: Optional[str] = None


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[str] = None  # Date of birth (YYYY-MM-DD)
    sex: Optional[str] = None  # M/F/Other
    marital_status: Optional[str] = None  # Single/Married/Divorced/Widowed
    address_data: Optional[AddressData] = None
    saved_payment_data: Optional[SavedPaymentData] = None


class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)  # Mandatory
    phone: str = Field(..., min_length=10)  # Mandatory, verified via OTP
    dob: str = Field(..., min_length=10)  # Mandatory (YYYY-MM-DD)


class UserLogin(BaseModel):
    username: str
    password: str


class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    marital_status: Optional[str] = None
    address_data: Optional[AddressData] = None
    saved_payment_data: Optional[SavedPaymentData] = None


class UserResponse(UserBase):
    role: str
    is_active: bool
    phone_verified: bool = False
    email_verified: bool = False
    created_at: datetime
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_encoders = {object: str}


class OTPSendRequest(BaseModel):
    """Send OTP to phone number during registration."""
    username: str = Field(..., min_length=3)
    email: EmailStr
    full_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=10)
    dob: str = Field(..., min_length=10)
    password: str = Field(..., min_length=8)


class OTPVerifyRegisterRequest(BaseModel):
    """Verify OTP and complete registration."""
    username: str
    email: EmailStr
    password: str
    full_name: str
    phone: str
    dob: str
    otp: str = Field(..., min_length=4, max_length=6)


class ChangePhoneRequest(BaseModel):
    """Request to change phone number (requires OTP verification)."""
    new_phone: str = Field(..., min_length=10)


class ChangePhoneVerifyRequest(BaseModel):
    """Verify new phone number with OTP."""
    new_phone: str
    otp: str = Field(..., min_length=4, max_length=6)


class EmailVerificationRequest(BaseModel):
    """Request email verification."""
    email: EmailStr
