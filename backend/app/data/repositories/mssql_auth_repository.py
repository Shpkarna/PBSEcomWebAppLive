"""SQL Server-backed auth repository implementation (Phase 7)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.data.repositories.mssql_base import MSSQLRepositoryBase
from app.domain.contracts.auth_repository import AuthRepository


class MSSQLAuthRepository(MSSQLRepositoryBase, AuthRepository):
    """SQL Server implementation for auth persistence operations."""

    def find_user_by_username(self, username: str, projection: Optional[dict] = None) -> Optional[dict]:
        return self.find_one_doc("users", {"username": username}, projection)

    def find_user_by_username_or_email(self, username: str, email: str) -> Optional[dict]:
        row = self._execute(
            "SELECT TOP (1) * FROM users WHERE username = ? OR email = ?",
            [username, email],
            fetchone=True,
        )
        return self._row_to_doc(self._spec("users"), row)

    def find_user_by_email_excluding_username(self, email: str, username: str) -> Optional[dict]:
        return self.find_one_doc("users", {"email": email, "username": {"$ne": username}})

    def find_user_by_phone_excluding_username(self, phone: str, username: str) -> Optional[dict]:
        return self.find_one_doc("users", {"phone": phone, "username": {"$ne": username}})

    def create_user(self, user_doc: dict) -> dict:
        return self.insert_one_doc("users", user_doc)

    def update_user_by_username(self, username: str, updates: dict) -> None:
        self.update_one_doc("users", {"username": username}, updates)

    def delete_pending_email_verifications(self, username: str, now: datetime) -> None:
        self.delete_many_docs(
            "email_verifications",
            {"username": username, "verified": False, "expires_at": {"$gt": now}},
        )

    def create_email_verification(self, verification_doc: dict) -> None:
        self.insert_one_doc("email_verifications", verification_doc)

    def find_valid_email_verification(self, username: str, token: str, now: datetime) -> Optional[dict]:
        return self.find_one_doc(
            "email_verifications",
            {
                "username": username,
                "token": token,
                "verified": False,
                "expires_at": {"$gt": now},
            },
        )

    def mark_email_verification_verified(self, verification_id: object, verified_at: datetime) -> None:
        self.update_one_doc(
            "email_verifications",
            {"id": str(verification_id)},
            {"verified": True, "verified_at": verified_at},
        )

    def find_session_by_id(self, session_id: str) -> Optional[dict]:
        return self.find_one_doc("sessions", {"id": session_id})

    def delete_session_by_id(self, session_id: str) -> None:
        self.delete_many_docs("sessions", {"id": session_id})
