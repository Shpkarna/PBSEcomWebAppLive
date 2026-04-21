"""Audit log utilities for the e-commerce app.

Phase 4: Delegates to ``LogRepository`` via the driver registry instead
of opening a dedicated ``MongoClient`` per call.
"""
from datetime import datetime
from app.data.repository_providers import get_log_repository


def log_event(action: str, user: str = "anonymous", details: dict | None = None, path: str = ""):
    """Insert an immutable audit log event."""
    repo = get_log_repository()
    event = {
        "action": action,
        "user": user,
        "path": path,
        "details": details or {},
        "created_at": datetime.utcnow(),
        "immutable": True,
    }
    repo.insert_event(event)


def get_logs(limit: int = 100):
    return get_log_repository().list_events(limit)
