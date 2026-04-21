"""MongoDB-backed auth repository implementation."""
from datetime import datetime
from typing import Optional

from app.database import get_collection
from app.domain.contracts.auth_repository import AuthRepository


class MongoAuthRepository(AuthRepository):
    """Mongo implementation for auth persistence operations."""

    def find_user_by_username(self, username: str, projection: Optional[dict] = None) -> Optional[dict]:
        return get_collection("users").find_one({"username": username}, projection)

    def find_user_by_username_or_email(self, username: str, email: str) -> Optional[dict]:
        return get_collection("users").find_one({"$or": [{"username": username}, {"email": email}]})

    def find_user_by_email_excluding_username(self, email: str, username: str) -> Optional[dict]:
        return get_collection("users").find_one({"email": email, "username": {"$ne": username}})

    def find_user_by_phone_excluding_username(self, phone: str, username: str) -> Optional[dict]:
        return get_collection("users").find_one({"phone": phone, "username": {"$ne": username}})

    def create_user(self, user_doc: dict) -> dict:
        doc = dict(user_doc)
        result = get_collection("users").insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    def update_user_by_username(self, username: str, updates: dict) -> None:
        get_collection("users").update_one({"username": username}, {"$set": updates})

    def delete_pending_email_verifications(self, username: str, now: datetime) -> None:
        get_collection("email_verifications").delete_many({
            "username": username,
            "verified": False,
            "expires_at": {"$gt": now},
        })

    def create_email_verification(self, verification_doc: dict) -> None:
        get_collection("email_verifications").insert_one(verification_doc)

    def find_valid_email_verification(self, username: str, token: str, now: datetime) -> Optional[dict]:
        return get_collection("email_verifications").find_one({
            "username": username,
            "token": token,
            "verified": False,
            "expires_at": {"$gt": now},
        })

    def mark_email_verification_verified(self, verification_id: object, verified_at: datetime) -> None:
        get_collection("email_verifications").update_one(
            {"_id": verification_id},
            {"$set": {"verified": True, "verified_at": verified_at}},
        )

    def find_session_by_id(self, session_id: str) -> Optional[dict]:
        return get_collection("sessions").find_one({"_id": session_id})

    def delete_session_by_id(self, session_id: str) -> None:
        get_collection("sessions").delete_one({"_id": session_id})
