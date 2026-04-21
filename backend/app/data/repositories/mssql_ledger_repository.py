"""SQL Server-backed ledger repository (Phase 7)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.data.repositories.mssql_base import MSSQLRepositoryBase
from app.domain.contracts.ledger_repository import LedgerRepository


class MSSQLLedgerRepository(MSSQLRepositoryBase, LedgerRepository):
    """SQL Server implementation for ledger entry persistence."""

    def add_entry(self, entry_doc: dict) -> dict:
        doc = dict(entry_doc)
        doc.setdefault("created_at", datetime.utcnow())
        return self.insert_one_doc("ledger", doc)

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
            date_filter: dict = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            query["created_at"] = date_filter
        return self.find_many_docs("ledger", query, order_by="created_at", descending=True)
