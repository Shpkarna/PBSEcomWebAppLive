"""OTP service for phone verification during registration and profile changes."""
import random
import string
import requests as http_requests
from datetime import datetime, timedelta, timezone
from app.database import get_collection
from app.utils.logger import log_event
from app.config import settings


def _send_via_msg91(phone: str, otp: str) -> bool:
    """
    Deliver OTP via MSG91 OTP API.

    MSG91 expects the mobile number with country code but without the leading '+',
    e.g. 919876543210 for an Indian number.
    The OTP template must be pre-approved on the MSG91 / DLT portal.
    """
    # Normalise: strip leading '+', keep digits only
    mobile = phone.lstrip("+").replace(" ", "").replace("-", "")

    url = "https://api.msg91.com/api/v5/otp"
    payload = {
        "template_id": settings.msg91_template_id,
        "mobile": mobile,
        "authkey": settings.msg91_authkey,
        "otp": otp,
        "sender": settings.msg91_sender_id,
    }
    headers = {"Content-Type": "application/json"}

    try:
        resp = http_requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if resp.ok and data.get("type") == "success":
            log_event(
                "otp_sms_sent",
                user=phone,
                details={"provider": "msg91", "response": data},
                path="/api/auth/register/send-otp",
            )
            return True
        log_event(
            "otp_sms_failed",
            user=phone,
            details={"provider": "msg91", "status": resp.status_code, "response": data},
            path="/api/auth/register/send-otp",
        )
        print(f"[OTP SERVICE] MSG91 error for {phone}: {data}")
        return False
    except Exception as exc:
        log_event(
            "otp_sms_failed",
            user=phone,
            details={"provider": "msg91", "error": str(exc)},
            path="/api/auth/register/send-otp",
        )
        print(f"[OTP SERVICE] MSG91 request failed for {phone}: {exc}")
        return False


class OTPService:
    """Service for managing One-Time Password (OTP) operations."""
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10  # OTP valid for 10 minutes
    MAX_ATTEMPTS = 3  # Max verification attempts before OTP expires
    
    @staticmethod
    def generate_otp() -> str:
        """Generate a random 6-digit OTP."""
        return ''.join(random.choices(string.digits, k=OTPService.OTP_LENGTH))
    
    @staticmethod
    def send_otp_to_phone(phone: str, otp: str) -> bool:
        """
        Send OTP to phone number via SMS.

        Uses MSG91 when MSG91_AUTHKEY and MSG91_TEMPLATE_ID are set in
        the environment / .env file.
        Falls back to console logging (dev/sandbox mode) when credentials are absent.

        Returns True if the message was dispatched successfully (or logged in dev mode).
        """
        has_any_msg91_config = any([
            settings.msg91_authkey,
            settings.msg91_template_id,
            settings.msg91_sender_id and settings.msg91_sender_id != "AIESHP",
        ])
        msg91_configured = all([
            settings.msg91_authkey,
            settings.msg91_template_id,
        ])

        if msg91_configured:
            return _send_via_msg91(phone, otp)

        if has_any_msg91_config:
            log_event(
                "otp_sms_failed",
                user=phone,
                details={
                    "provider": "msg91",
                    "reason": "incomplete_configuration",
                    "authkey_set": bool(settings.msg91_authkey),
                    "template_id_set": bool(settings.msg91_template_id),
                    "sender_id": settings.msg91_sender_id,
                },
                path="/api/auth/register/send-otp",
            )
            print(
                "[OTP SERVICE] MSG91 configuration incomplete: "
                f"authkey_set={bool(settings.msg91_authkey)}, "
                f"template_id_set={bool(settings.msg91_template_id)}, "
                f"sender_id={settings.msg91_sender_id}"
            )
            return False

        # --- Dev / sandbox fallback: print to console ---
        print(f"[OTP SERVICE - DEV MODE] OTP for {phone}: {otp}")
        print("[OTP SERVICE - DEV MODE] Set MSG91_AUTHKEY and MSG91_TEMPLATE_ID in .env to enable real SMS.")
        log_event(
            "otp_sent_devmode",
            user=phone,
            details={"action": "otp_send", "mode": "console", "otp_partial": f"***{otp[-2:]}"},
            path="/api/auth/register/send-otp",
        )
        return True
    
    @staticmethod
    def create_otp_record(phone: str, purpose: str = "registration") -> dict:
        """
        Create a new OTP record for phone verification.
        
        Args:
            phone: Phone number to verify
            purpose: Purpose of OTP (registration, phone_change, etc.)
            
        Returns:
            dict: Dictionary containing 'otp' and 'expires_at'
        """
        otp = OTPService.generate_otp()
        otp_col = get_collection("otp_records")
        
        # Delete any existing OTP records for this phone
        otp_col.delete_many({"phone": phone, "purpose": purpose, "verified": False})
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTPService.OTP_EXPIRY_MINUTES)
        
        otp_record = {
            "phone": phone,
            "purpose": purpose,
            "otp": otp,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "verified": False,
            "verification_attempts": 0,
        }
        
        result = otp_col.insert_one(otp_record)
        
        # Send OTP to phone and surface provider failures to caller.
        otp_sent = OTPService.send_otp_to_phone(phone, otp)
        
        log_event(
            "otp_created",
            user=phone,
            details={"action": "otp_creation", "purpose": purpose},
            path="/api/auth/register/send-otp",
        )
        
        return {
            "otp_sent": otp_sent,
            "expires_at": expires_at,
            "message": (
                f"OTP sent to {phone}. Valid for {OTPService.OTP_EXPIRY_MINUTES} minutes."
                if otp_sent
                else "Failed to send OTP to phone. Please try again later."
            ),
        }
    
    @staticmethod
    def verify_otp(phone: str, otp: str, purpose: str = "registration") -> dict:
        """
        Verify the OTP provided by the user.
        
        Args:
            phone: Phone number that OTP was sent to
            otp: OTP code provided by user
            purpose: Purpose of OTP (registration, phone_change, etc.)
            
        Returns:
            dict: {
                "success": bool,
                "message": str,
                "otp_record_id": str (if successful)
            }
        """
        otp_col = get_collection("otp_records")
        
        # Find active OTP record
        otp_record = otp_col.find_one({
            "phone": phone,
            "purpose": purpose,
            "verified": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        })
        
        if not otp_record:
            log_event(
                "otp_verification_failed",
                user=phone,
                details={"reason": "no_valid_otp_found", "purpose": purpose},
                path="/api/auth/register/verify-otp",
            )
            return {
                "success": False,
                "message": "No valid OTP found for this phone. Please request a new OTP.",
            }
        
        # Check if max attempts exceeded
        if otp_record.get("verification_attempts", 0) >= OTPService.MAX_ATTEMPTS:
            log_event(
                "otp_verification_failed",
                user=phone,
                details={"reason": "max_attempts_exceeded", "purpose": purpose},
                path="/api/auth/register/verify-otp",
            )
            return {
                "success": False,
                "message": f"Max verification attempts exceeded. Please request a new OTP.",
            }
        
        # Verify OTP
        if otp_record["otp"] != otp:
            # Increment attempts
            otp_col.update_one(
                {"_id": otp_record["_id"]},
                {"$inc": {"verification_attempts": 1}}
            )
            attempts_left = OTPService.MAX_ATTEMPTS - otp_record.get("verification_attempts", 0) - 1
            log_event(
                "otp_verification_failed",
                user=phone,
                details={"reason": "invalid_otp", "attempts_left": attempts_left, "purpose": purpose},
                path="/api/auth/register/verify-otp",
            )
            return {
                "success": False,
                "message": f"Invalid OTP. {attempts_left} attempts left.",
                "attempts_left": attempts_left,
            }
        
        # OTP is valid - mark as verified
        otp_col.update_one(
            {"_id": otp_record["_id"]},
            {"$set": {"verified": True, "verified_at": datetime.now(timezone.utc)}}
        )
        
        log_event(
            "otp_verified",
            user=phone,
            details={"purpose": purpose},
            path="/api/auth/register/verify-otp",
        )
        
        return {
            "success": True,
            "message": "OTP verified successfully.",
            "otp_record_id": str(otp_record["_id"]),
        }
    
    @staticmethod
    def get_verified_otp_record(phone: str, purpose: str = "registration") -> dict:
        """
        Retrieve a verified OTP record for the given phone and purpose.
        
        Args:
            phone: Phone number
            purpose: Purpose of OTP
            
        Returns:
            dict: The verified OTP record, or None if not found
        """
        otp_col = get_collection("otp_records")
        otp_record = otp_col.find_one({
            "phone": phone,
            "purpose": purpose,
            "verified": True,
            "verified_at": {"$gt": datetime.now(timezone.utc) - timedelta(minutes=OTPService.OTP_EXPIRY_MINUTES)},
        })
        return otp_record
    
    @staticmethod
    def mark_otp_used(otp_record_id: str):
        """Mark an OTP record as used (after successful registration/phone change)."""
        otp_col = get_collection("otp_records")
        otp_col.update_one(
            {"_id": otp_record_id},
            {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
        )
