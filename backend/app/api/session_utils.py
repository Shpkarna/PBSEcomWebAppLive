"""Session management utilities.

Session rules:
- For a given (client_ip, client_mac) pair, only ONE session can be valid.
- Within a valid session a JWT is created only when no active (non-expired)
  token has already been issued for that session.  If a valid token exists the
  same token string is returned instead of minting a new one.
"""
from datetime import timedelta, datetime
from uuid import uuid4
from typing import Optional, Tuple
from app.data.repository_providers import get_utility_repository
from app.config import settings


def _is_session_alive(session: dict, now: datetime) -> bool:
    """Return True when the session has not expired and is not inactive."""
    if session.get("expires_at") and session["expires_at"] < now:
        return False
    inactivity_limit = timedelta(minutes=settings.session_inactivity_minutes)
    last_activity = session.get("last_activity", session.get("created_at", now))
    if now - last_activity > inactivity_limit:
        return False
    return True


def get_or_create_session(
    username: str,
    client_ip: str,
    client_mac: str,
) -> Tuple[str, bool]:
    """Return (session_token, reused) for the given user + device.

    * If a live session already exists for this (client_ip, client_mac) return
      it and set *reused* = True so the caller knows not to mint a new JWT.
    * Otherwise invalidate any stale sessions for the same IP+MAC, create a
      fresh session and return *reused* = False.
    """
    sessions = get_utility_repository()
    now = datetime.utcnow()

    # Look for an existing session on this exact device fingerprint.
    existing = sessions.find_session({
        "username": username,
        "client_ip": client_ip,
        "client_mac": client_mac,
    })

    if existing and _is_session_alive(existing, now):
        # Check whether a non-expired token was already issued in this session.
        token_expiry = existing.get("token_expires_at")
        if token_expiry and token_expiry > now and existing.get("access_token"):
            # Valid session with a live token – reuse everything.
            sessions.update_session(
                existing["_id"],
                {"last_activity": now},
            )
            return existing["_id"], True
        # Session alive but token expired/missing – caller will mint a new JWT
        # and store it via `store_token_in_session`.
        sessions.update_session(
            existing["_id"],
            {"last_activity": now},
        )
        return existing["_id"], False

    # Invalidate any previous sessions for this IP+MAC (one session per device).
    sessions.delete_session({
        "username": username,
        "client_ip": client_ip,
        "client_mac": client_mac,
    })

    session_token = str(uuid4())
    expiry = now + timedelta(minutes=settings.session_expire_minutes)
    sessions.create_session({
        "_id": session_token,
        "username": username,
        "client_ip": client_ip,
        "client_mac": client_mac,
        "created_at": now,
        "expires_at": expiry,
        "last_activity": now,
        "access_token": None,
        "token_expires_at": None,
    })
    return session_token, False


def store_token_in_session(session_token: str, access_token: str, token_expires_at: datetime):
    """Persist the JWT string and its expiry inside the session document."""
    get_utility_repository().update_session(
        session_token,
        {
            "access_token": access_token,
            "token_expires_at": token_expires_at,
        },
    )


def get_existing_token(session_token: str) -> Optional[str]:
    """Return the stored JWT for *session_token* if it is still valid."""
    session = get_utility_repository().find_session({"_id": session_token})
    if not session:
        return None
    now = datetime.utcnow()
    token_expiry = session.get("token_expires_at")
    if token_expiry and token_expiry > now and session.get("access_token"):
        return session["access_token"]
    return None


def validate_session(session_token: str) -> Optional[str]:
    """Validate session and return the username if alive, else None."""
    repo = get_utility_repository()
    session = repo.find_session({"_id": session_token})
    if not session:
        return None
    now = datetime.utcnow()
    if not _is_session_alive(session, now):
        repo.delete_session({"_id": session_token})
        return None
    repo.update_session(session_token, {"last_activity": now})
    return session["username"]


def invalidate_sessions_for_device(username: str, client_ip: str, client_mac: str):
    """Remove all sessions for a specific user + device fingerprint."""
    get_utility_repository().delete_session({
        "username": username,
        "client_ip": client_ip,
        "client_mac": client_mac,
    })
