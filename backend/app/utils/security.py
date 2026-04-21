"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.data.repository_providers import get_utility_repository

# Security
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def _coerce_datetime(value) -> Optional[datetime]:
    """Coerce a value to datetime, handling strings stored in MySQL LONGTEXT columns."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            pass
    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using bcrypt"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token and validate it against the DB-backed session.

    The session document now stores the issued token string.  If the presented
    token does not match what was recorded the request is rejected – this
    prevents use of old JWTs after a new one has been minted for the session.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username = payload.get("sub")
        session_id = payload.get("sid")
        if not username or not session_id:
            return None

        utility_repo = get_utility_repository()
        session = utility_repo.find_session_by_id(session_id)
        if not session or session.get("username") != username:
            return None

        now = datetime.utcnow()
        expires_at = _coerce_datetime(session.get("expires_at"))
        if expires_at and expires_at < now:
            utility_repo.delete_session({"_id": session_id})
            return None

        inactivity_limit = timedelta(minutes=settings.session_inactivity_minutes)
        last_activity = (
            _coerce_datetime(session.get("last_activity"))
            or _coerce_datetime(session.get("created_at"))
            or now
        )
        if now - last_activity > inactivity_limit:
            utility_repo.delete_session({"_id": session_id})
            return None

        # Ensure the presented token is the one currently associated with the session.
        stored_token = session.get("access_token")
        if stored_token and stored_token != token:
            return None

        utility_repo.update_session(session_id, {"last_activity": now})
        return payload
    except JWTError:
        return None


def get_token_from_credentials(credentials: HTTPAuthorizationCredentials) -> str:
    """Extract token from HTTP credentials"""
    return credentials.credentials
