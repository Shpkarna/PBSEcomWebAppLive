"""MongoDB-backed audit log repository."""
from datetime import datetime

from app.config import settings
from app.database import get_database
from app.domain.contracts.log_repository import LogRepository


class MongoLogRepository(LogRepository):
    """Mongo implementation for audit log persistence.

    Uses the shared ``get_database`` connection (via the configured
    ``log_database`` name) instead of opening a new MongoClient per call,
    fixing the connection-pooling debt identified in the Phase 0 catalog.
    """

    def _col(self):
        from pymongo import MongoClient
        # Log DB is a separate database from the main app DB.
        # We reuse the same MongoClient that database.py manages.
        from app.database import get_database as _get_db
        db = _get_db()
        client = db.client
        log_db = client[settings.log_database]
        return log_db["audit_logs"]

    def insert_event(self, event: dict) -> None:
        self._col().insert_one(event)

    def list_events(self, limit: int = 100) -> list[dict]:
        docs = list(self._col().find().sort("created_at", -1).limit(limit))
        for d in docs:
            d["id"] = str(d.pop("_id", ""))
        return docs
