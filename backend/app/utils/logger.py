"""Audit log utilities for the e-commerce app."""
from datetime import datetime
from app.config import settings
from pymongo import MongoClient


def _get_log_collection():
    client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
    log_db = client[settings.log_database]
    return log_db["audit_logs"], client


def log_event(action: str, user: str = "anonymous", details: dict | None = None, path: str = ""):
    """Insert an immutable audit log event."""
    collection, client = _get_log_collection()
    try:
        event = {
            "action": action,
            "user": user,
            "path": path,
            "details": details or {},
            "created_at": datetime.utcnow(),
            "immutable": True,
        }
        collection.insert_one(event)
    finally:
        client.close()


def get_logs(limit: int = 100):
    collection, client = _get_log_collection()
    try:
        return list(collection.find().sort("created_at", -1).limit(limit))
    finally:
        client.close()
