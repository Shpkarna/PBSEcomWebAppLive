"""Repository contract for shared utility persistence dependencies."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional


class UtilityRepository(ABC):
    """Storage-agnostic gateway used by utility modules."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Sessions
    # ------------------------------------------------------------------

    @abstractmethod
    def find_session(self, filter_doc: dict) -> Optional[dict]:
        """Return a session document matching filter_doc."""

    @abstractmethod
    def create_session(self, doc: dict) -> None:
        """Insert a session document."""

    @abstractmethod
    def update_session(self, session_id: Any, updates: dict) -> None:
        """Apply $set updates to a session by _id."""

    @abstractmethod
    def delete_session(self, filter_doc: dict) -> int:
        """Delete sessions matching filter. Return deleted_count."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Users (admin / rbac management)
    # ------------------------------------------------------------------

    @abstractmethod
    def list_users(
        self,
        filter_doc: dict,
        projection: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """Return users matching filter with pagination and optional projection."""

    @abstractmethod
    def find_user(self, filter_doc: dict, projection: Optional[dict] = None) -> Optional[dict]:
        """Return a single user matching filter_doc."""

    @abstractmethod
    def create_user_admin(self, doc: dict) -> dict:
        """Insert user document and return stored document with id field."""

    @abstractmethod
    def update_user(self, filter_doc: dict, updates: dict) -> int:
        """Apply $set updates to matching user. Return matched_count."""

    @abstractmethod
    def delete_user(self, filter_doc: dict) -> int:
        """Delete user matching filter. Return deleted_count."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — RBAC
    # ------------------------------------------------------------------

    @abstractmethod
    def update_role_permissions(self, role: str, functionalities: list[str], now: datetime) -> None:
        """Upsert role_permissions and rebuild role_functionality_mappings."""

    @abstractmethod
    def update_user_role_mapping(self, username: str, new_role: str, now: datetime) -> None:
        """Upsert user_role_mappings row for username."""

    @abstractmethod
    def list_role_permissions(self) -> list[dict]:
        """Return all role permission rows."""

    @abstractmethod
    def find_user_role_mapping(self, username: str) -> Optional[dict]:
        """Return explicit role mapping row for username if present."""

    # ------------------------------------------------------------------
    # Phase 3: Named operations — User search / uniqueness helpers
    # ------------------------------------------------------------------

    @abstractmethod
    def search_users(
        self, search_term: Optional[str], skip: int = 0, limit: int = 50
    ) -> list[dict]:
        """Search users by username/email/full_name pattern with pagination."""

    @abstractmethod
    def find_user_by_email_excluding(self, email: str, exclude_username: str) -> Optional[dict]:
        """Find user with given email but different username (uniqueness check)."""

    @abstractmethod
    def find_user_by_phone_excluding(self, phone: str, exclude_username: str) -> Optional[dict]:
        """Find user with given phone but different username (uniqueness check)."""

    # ------------------------------------------------------------------
    # Phase 3: Named operations — OTP records
    # ------------------------------------------------------------------

    @abstractmethod
    def delete_unverified_otp_records(self, phone: str, purpose: str) -> None:
        """Delete unverified OTP records for phone/purpose."""

    @abstractmethod
    def create_otp_record(self, doc: dict) -> dict:
        """Insert OTP record and return stored doc."""

    @abstractmethod
    def find_active_otp(self, phone: str, purpose: str, now: datetime) -> Optional[dict]:
        """Find active (unexpired, unverified) OTP record."""

    @abstractmethod
    def increment_otp_attempts(self, otp_id: Any) -> None:
        """Increment verification_attempts counter on OTP record."""

    @abstractmethod
    def mark_otp_verified(self, otp_id: Any, verified_at: datetime) -> None:
        """Mark OTP record as verified."""

    @abstractmethod
    def find_verified_otp(self, phone: str, purpose: str, since: datetime) -> Optional[dict]:
        """Find verified OTP record created after given time."""

    @abstractmethod
    def mark_otp_used(self, otp_id: Any, used_at: datetime) -> None:
        """Mark OTP record as used."""

    # ------------------------------------------------------------------
    # Phase 4: Named operations — Atomic counter
    # ------------------------------------------------------------------

    @abstractmethod
    def next_counter_id(self, counter_key: str) -> int:
        """Atomically increment and return the next sequence value for *counter_key*."""

    # ------------------------------------------------------------------
    # Phase 4: Named operations — Session lookup by id
    # ------------------------------------------------------------------

    @abstractmethod
    def find_session_by_id(self, session_id: str) -> Optional[dict]:
        """Return a session document by its id."""

