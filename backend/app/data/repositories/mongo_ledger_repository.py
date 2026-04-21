"""MongoDB-backed ledger repository."""
from datetime import datetime
from typing import Optional

from app.database import get_collection
from app.domain.contracts.ledger_repository import LedgerRepository


class MongoLedgerRepository(LedgerRepository):
    """Mongo implementation for financial ledger operations."""

    def _col(self):
        return get_collection("ledger")

    def add_entry(self, entry_doc: dict) -> dict:
        entry_doc.setdefault("created_at", datetime.utcnow())
        res = self._col().insert_one(entry_doc)
        entry_doc["_id"] = res.inserted_id
        entry_doc["id"] = str(entry_doc.pop("_id"))
        return entry_doc

    def list_entries(
        self,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict]:
        query: dict = {}
        if category:
            query["category"] = category
        if start_date or end_date:
            dq: dict = {}
            if start_date:
                dq["$gte"] = start_date
            if end_date:
                dq["$lte"] = end_date
            query["created_at"] = dq
        docs = list(self._col().find(query).sort("created_at", -1))
        for d in docs:
            d["id"] = str(d.pop("_id"))
        return docs
