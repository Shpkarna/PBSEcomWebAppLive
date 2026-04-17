"""
Configuration settings for the FastAPI application
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal


class Settings(BaseSettings):
    """Application settings"""

    # Package Option: sandbox, trial, or prod (MANDATORY at build time)
    package_option: Literal["sandbox", "trial", "prod"] = "sandbox"

    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "ecomdb"
    log_database: str = "logDB"

    # Session Configuration
    session_cookie_name: str = "session_id"
    session_expire_minutes: int = 60
    session_inactivity_minutes: int = 2

    # JWT Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API Configuration
    api_title: str = "E-Commerce API"
    api_version: str = "1.0.0"
    api_description: str = "FastAPI-based E-Commerce Platform"

    # Admin Configuration
    admin_username: str = "admin"
    admin_password: str = "Qsrt#09-MWQ"
    admin_email: str = "admin@paultrades.com"

    # GST Configuration
    default_gst_rate: float = 0.18  # 18% GST

    # Razorpay Configuration
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_currency: str = "INR"

    # MSG91 SMS Configuration
    # Set these to enable real SMS delivery; leave blank to fall back to console logging.
    # Obtain authkey and template_id from https://msg91.com/
    msg91_authkey: str = ""
    msg91_template_id: str = ""   # DLT-registered template ID
    msg91_sender_id: str = "AIESHP"  # 6-char sender ID registered with MSG91
    enable_mobile_otp_verification: bool = True
    enable_email_verification: bool = False

    # Public API key for /public/api/ endpoints
    public_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
