"""MySQL-backed utility repository implementation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.data.mysql_client import mysql_connection
from app.data.repositories.mysql_base import MySQLRepositoryBase
from app.domain.contracts.utility_repository import UtilityRepository


class MySQLUtilityRepository(MySQLRepositoryBase, UtilityRepository):
    """MySQL implementation for shared utility persistence dependencies."""

    def find_session(self, filter_doc: dict) -> Optional[dict]:
        return self.find_one_doc("sessions", filter_doc)

    def create_session(self, doc: dict) -> None:
        self.insert_one_doc("sessions", doc)

    def update_session(self, session_id: Any, updates: dict) -> None:
        self.update_one_doc("sessions", {"id": str(session_id)}, updates)

    def delete_session(self, filter_doc: dict) -> int:
        return self.delete_many_docs("sessions", filter_doc)

    def list_users(
        self,
        filter_doc: dict,
        projection: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        return self.find_many_docs(
            "users",
            filter_doc,
            projection=projection,
            skip=skip,
            limit=limit,
        )

    def find_user(self, filter_doc: dict, projection: Optional[dict] = None) -> Optional[dict]:
        return self.find_one_doc("users", filter_doc, projection)

    def create_user_admin(self, doc: dict) -> dict:
        return self.insert_one_doc("users", doc)

    def update_user(self, filter_doc: dict, updates: dict) -> int:
        return self.update_one_doc("users", filter_doc, updates)

    def delete_user(self, filter_doc: dict) -> int:
        return self.delete_many_docs("users", filter_doc)

    def update_role_permissions(self, role: str, functionalities: list[str], now: datetime) -> None:
        self.update_one_doc(
            "role_permissions",
            {"role": role},
            {"role": role, "functionalities": functionalities, "updated_at": now},
            upsert=True,
        )
        self.delete_many_docs("role_functionality_mappings", {"role": role})
        for code in functionalities:
            self.insert_one_doc(
                "role_functionality_mappings",
                {"role": role, "functionality_code": code, "created_at": now},
            )

    def update_user_role_mapping(self, username: str, new_role: str, now: datetime) -> None:
        self.update_one_doc(
            "user_role_mappings",
            {"username": username},
            {"username": username, "role": new_role, "updated_at": now},
            upsert=True,
        )

    def list_role_permissions(self) -> list[dict]:
        return self.find_many_docs("role_permissions", {})

    def find_user_role_mapping(self, username: str) -> Optional[dict]:
        return self.find_one_doc("user_role_mappings", {"username": username})

    def search_users(self, search_term: Optional[str], skip: int = 0, limit: int = 50) -> list[dict]:
        spec = self._spec("users")
        if search_term and search_term.strip():
            pattern = f"%{search_term.strip()}%"
            rows = self._execute(
                (
                    "SELECT * FROM users "
                    "WHERE LOWER(username) LIKE LOWER(%s) "
                    "OR LOWER(email) LIKE LOWER(%s) "
                    "OR LOWER(full_name) LIKE LOWER(%s) "
                    "LIMIT %s OFFSET %s"
                ),
                [pattern, pattern, pattern, int(limit), int(skip)],
                fetchall=True,
            )
        else:
            rows = self._execute(
                "SELECT * FROM users LIMIT %s OFFSET %s",
                [int(limit), int(skip)],
                fetchall=True,
            )
        return [self._row_to_doc(spec, row) for row in rows or [] if row]

    def find_user_by_email_excluding(self, email: str, exclude_username: str) -> Optional[dict]:
        return self.find_one_doc("users", {"email": email, "username": {"$ne": exclude_username}})

    def find_user_by_phone_excluding(self, phone: str, exclude_username: str) -> Optional[dict]:
        return self.find_one_doc("users", {"phone": phone, "username": {"$ne": exclude_username}})

    def delete_unverified_otp_records(self, phone: str, purpose: str) -> None:
        self.delete_many_docs("otp_records", {"phone": phone, "purpose": purpose, "verified": False})

    def create_otp_record(self, doc: dict) -> dict:
        return self.insert_one_doc("otp_records", doc)

    def find_active_otp(self, phone: str, purpose: str, now: datetime) -> Optional[dict]:
        return self.find_one_doc(
            "otp_records",
            {"phone": phone, "purpose": purpose, "verified": False, "expires_at": {"$gt": now}},
        )

    def increment_otp_attempts(self, otp_id: Any) -> None:
        self._execute(
            "UPDATE otp_records SET verification_attempts = verification_attempts + 1 WHERE id = %s",
            [str(otp_id)],
        )

    def mark_otp_verified(self, otp_id: Any, verified_at: datetime) -> None:
        self.update_one_doc(
            "otp_records",
            {"id": str(otp_id)},
            {"verified": True, "verified_at": verified_at},
        )

    def find_verified_otp(self, phone: str, purpose: str, since: datetime) -> Optional[dict]:
        return self.find_one_doc(
            "otp_records",
            {"phone": phone, "purpose": purpose, "verified": True, "verified_at": {"$gt": since}},
        )

    def mark_otp_used(self, otp_id: Any, used_at: datetime) -> None:
        self.update_one_doc(
            "otp_records",
            {"id": str(otp_id)},
            {"used": True, "used_at": used_at},
        )

    def next_counter_id(self, counter_key: str) -> int:
        with mysql_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    (
                        "INSERT INTO counters (counter_key, seq, updated_at, payload_json) "
                        "VALUES (%s, LAST_INSERT_ID(1), %s, NULL) "
                        "ON DUPLICATE KEY UPDATE "
                        "seq = LAST_INSERT_ID(seq + 1), updated_at = VALUES(updated_at)"
                    ),
                    [counter_key, datetime.utcnow()],
                )
                cursor.execute("SELECT LAST_INSERT_ID() AS seq")
                row = cursor.fetchone() or {}
        return int(row.get("seq", 0))

    def find_session_by_id(self, session_id: str) -> Optional[dict]:
        return self.find_one_doc("sessions", {"id": session_id})