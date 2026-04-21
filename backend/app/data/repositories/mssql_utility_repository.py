"""SQL Server-backed utility repository implementation (Phase 7)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.data.mssql_client import mssql_connection, mssql_transaction
from app.data.repositories.mssql_base import MSSQLRepositoryBase
from app.domain.contracts.utility_repository import UtilityRepository


class MSSQLUtilityRepository(MSSQLRepositoryBase, UtilityRepository):
    """SQL Server implementation for shared utility persistence dependencies."""

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
                    "WHERE LOWER(username) LIKE LOWER(?) "
                    "OR LOWER(email) LIKE LOWER(?) "
                    "OR LOWER(full_name) LIKE LOWER(?) "
                    "ORDER BY id ASC "
                    "OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
                ),
                [pattern, pattern, pattern, int(skip), int(limit)],
                fetchall=True,
            )
        else:
            rows = self._execute(
                "SELECT * FROM users ORDER BY id ASC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
                [int(skip), int(limit)],
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
            "UPDATE otp_records SET verification_attempts = verification_attempts + 1 WHERE id = ?",
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
        """Atomically increment (or create) a named counter and return the new value.

        Uses a MERGE statement to avoid a separate SELECT + INSERT/UPDATE race.
        """
        now = datetime.utcnow()
        with mssql_transaction():
            with mssql_connection() as connection:
                cursor = connection.cursor()
                # MERGE with HOLDLOCK prevents concurrent inserts from racing
                cursor.execute(
                    """
                    MERGE counters WITH (HOLDLOCK) AS target
                    USING (SELECT ? AS counter_key) AS source
                      ON target.counter_key = source.counter_key
                    WHEN MATCHED THEN
                        UPDATE SET seq = seq + 1, updated_at = ?
                    WHEN NOT MATCHED THEN
                        INSERT (counter_key, seq, updated_at, payload_json)
                        VALUES (source.counter_key, 1, ?, NULL);
                    """,
                    [counter_key, now, now],
                )
                cursor.execute(
                    "SELECT seq FROM counters WHERE counter_key = ?",
                    [counter_key],
                )
                row = cursor.fetchone()
        return int(row[0]) if row else 0

    def find_session_by_id(self, session_id: str) -> Optional[dict]:
        return self.find_one_doc("sessions", {"id": session_id})
