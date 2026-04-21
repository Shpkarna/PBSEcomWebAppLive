"""MongoDB-backed utility repository implementation."""
import re as _re
from datetime import datetime
from typing import Any, Optional

from app.database import get_collection
from app.domain.contracts.utility_repository import UtilityRepository


class MongoUtilityRepository(UtilityRepository):
    """Mongo implementation for shared utility persistence dependencies."""

    def _sessions_collection(self):
        return get_collection("sessions")

    def _role_permissions_collection(self):
        return get_collection("role_permissions")

    def _role_functionality_mappings_collection(self):
        return get_collection("role_functionality_mappings")

    def _user_role_mappings_collection(self):
        return get_collection("user_role_mappings")

    def _users_collection(self):
        return get_collection("users")

    def _counters_collection(self):
        return get_collection("counters")

    def _otp_records_collection(self):
        return get_collection("otp_records")

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Sessions
    # ------------------------------------------------------------------

    def find_session(self, filter_doc: dict) -> Optional[dict]:
        return self._sessions_collection().find_one(filter_doc)

    def create_session(self, doc: dict) -> None:
        self._sessions_collection().insert_one(doc)

    def update_session(self, session_id, updates: dict) -> None:
        self._sessions_collection().update_one({"_id": session_id}, {"$set": updates})

    def delete_session(self, filter_doc: dict) -> int:
        res = self._sessions_collection().delete_many(filter_doc)
        return int(res.deleted_count)

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Users
    # ------------------------------------------------------------------

    def list_users(
        self,
        filter_doc: dict,
        projection: Optional[dict] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        cursor = self._users_collection().find(filter_doc, projection or {})
        return list(cursor.skip(skip).limit(limit))

    def find_user(self, filter_doc: dict, projection: Optional[dict] = None) -> Optional[dict]:
        kwargs: dict = {}
        if projection:
            kwargs["projection"] = projection
        return self._users_collection().find_one(filter_doc, **kwargs)

    def create_user_admin(self, doc: dict) -> dict:
        res = self._users_collection().insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    def update_user(self, filter_doc: dict, updates: dict) -> int:
        res = self._users_collection().update_one(filter_doc, {"$set": updates})
        return int(res.matched_count)

    def delete_user(self, filter_doc: dict) -> int:
        res = self._users_collection().delete_one(filter_doc)
        return int(res.deleted_count)

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — RBAC
    # ------------------------------------------------------------------

    def update_role_permissions(self, role: str, functionalities: list[str], now: datetime) -> None:
        rp = self._role_permissions_collection()
        rp.update_one(
            {"_id": role},
            {"$set": {"functionalities": functionalities, "updated_at": now}},
            upsert=True,
        )
        rfm = self._role_functionality_mappings_collection()
        rfm.delete_many({"role": role})
        if functionalities:
            rfm.insert_many(
                [{"role": role, "functionality_code": c, "created_at": now} for c in functionalities]
            )

    def update_user_role_mapping(self, username: str, new_role: str, now: datetime) -> None:
        self._user_role_mappings_collection().update_one(
            {"username": username},
            {"$set": {"role": new_role, "updated_at": now}},
            upsert=True,
        )

    def list_role_permissions(self) -> list[dict]:
        return list(self._role_permissions_collection().find({}))

    def find_user_role_mapping(self, username: str) -> Optional[dict]:
        return self._user_role_mappings_collection().find_one({"username": username})

    # ------------------------------------------------------------------
    # Phase 3: Named operations — User search / uniqueness helpers
    # ------------------------------------------------------------------

    def search_users(
        self, search_term: Optional[str], skip: int = 0, limit: int = 50
    ) -> list[dict]:
        query: dict = {}
        if search_term and search_term.strip():
            pattern = _re.escape(search_term.strip())
            query["$or"] = [
                {"username": {"$regex": pattern, "$options": "i"}},
                {"email": {"$regex": pattern, "$options": "i"}},
                {"full_name": {"$regex": pattern, "$options": "i"}},
            ]
        cursor = self._users_collection().find(query)
        return list(cursor.skip(skip).limit(limit))

    def find_user_by_email_excluding(self, email: str, exclude_username: str) -> Optional[dict]:
        return self._users_collection().find_one(
            {"email": email, "username": {"$ne": exclude_username}}
        )

    def find_user_by_phone_excluding(self, phone: str, exclude_username: str) -> Optional[dict]:
        return self._users_collection().find_one(
            {"phone": phone, "username": {"$ne": exclude_username}}
        )

    # ------------------------------------------------------------------
    # Phase 3: Named operations — OTP records
    # ------------------------------------------------------------------

    def delete_unverified_otp_records(self, phone: str, purpose: str) -> None:
        self._otp_records_collection().delete_many(
            {"phone": phone, "purpose": purpose, "verified": False}
        )

    def create_otp_record(self, doc: dict) -> dict:
        res = self._otp_records_collection().insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    def find_active_otp(self, phone: str, purpose: str, now: datetime) -> Optional[dict]:
        return self._otp_records_collection().find_one({
            "phone": phone,
            "purpose": purpose,
            "verified": False,
            "expires_at": {"$gt": now},
        })

    def increment_otp_attempts(self, otp_id: Any) -> None:
        self._otp_records_collection().update_one(
            {"_id": otp_id},
            {"$inc": {"verification_attempts": 1}},
        )

    def mark_otp_verified(self, otp_id: Any, verified_at: datetime) -> None:
        self._otp_records_collection().update_one(
            {"_id": otp_id},
            {"$set": {"verified": True, "verified_at": verified_at}},
        )

    def find_verified_otp(self, phone: str, purpose: str, since: datetime) -> Optional[dict]:
        return self._otp_records_collection().find_one({
            "phone": phone,
            "purpose": purpose,
            "verified": True,
            "verified_at": {"$gt": since},
        })

    def mark_otp_used(self, otp_id: Any, used_at: datetime) -> None:
        self._otp_records_collection().update_one(
            {"_id": otp_id},
            {"$set": {"used": True, "used_at": used_at}},
        )

    # ------------------------------------------------------------------
    # Phase 4: Atomic counter
    # ------------------------------------------------------------------

    def next_counter_id(self, counter_key: str) -> int:
        from pymongo import ReturnDocument
        doc = self._counters_collection().find_one_and_update(
            {"_id": counter_key},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return int(doc["seq"])

    # ------------------------------------------------------------------
    # Phase 4: Session lookup by id
    # ------------------------------------------------------------------

    def find_session_by_id(self, session_id: str) -> Optional[dict]:
        return self._sessions_collection().find_one({"_id": session_id})
