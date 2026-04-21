"""Repository contract for authentication-related persistence operations."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class AuthRepository(ABC):
    """Storage-agnostic contract for auth/user/email-verification/session data."""

    @abstractmethod
    def find_user_by_username(self, username: str, projection: Optional[dict] = None) -> Optional[dict]:
        """Return user document by username."""

    @abstractmethod
    def find_user_by_username_or_email(self, username: str, email: str) -> Optional[dict]:
        """Return a user matching username or email."""

    @abstractmethod
    def find_user_by_email_excluding_username(self, email: str, username: str) -> Optional[dict]:
        """Return a user matching email and not matching username."""

    @abstractmethod
    def find_user_by_phone_excluding_username(self, phone: str, username: str) -> Optional[dict]:
        """Return a user matching phone and not matching username."""

    @abstractmethod
    def create_user(self, user_doc: dict) -> dict:
        """Insert user and return inserted document with _id."""

    @abstractmethod
    def update_user_by_username(self, username: str, updates: dict) -> None:
        """Apply partial updates for a user."""

    @abstractmethod
    def delete_pending_email_verifications(self, username: str, now: datetime) -> None:
        """Delete unverified and non-expired email verification records."""

    @abstractmethod
    def create_email_verification(self, verification_doc: dict) -> None:
        """Create email verification record."""

    @abstractmethod
    def find_valid_email_verification(self, username: str, token: str, now: datetime) -> Optional[dict]:
        """Find valid non-expired email verification token record."""

    @abstractmethod
    def mark_email_verification_verified(self, verification_id: object, verified_at: datetime) -> None:
        """Mark verification record as completed."""

    @abstractmethod
    def find_session_by_id(self, session_id: str) -> Optional[dict]:
        """Return session document by id."""

    @abstractmethod
    def delete_session_by_id(self, session_id: str) -> None:
        """Delete session by id."""
