"""Repository contract for financial ledger persistence operations.

Phase 2 added this contract to give ledger routes a named abstract interface
instead of accessing a raw MongoDB collection through the order/cart gateway.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class LedgerRepository(ABC):
    """Storage-agnostic gateway for financial ledger operations."""

    @abstractmethod
    def add_entry(self, entry_doc: dict) -> dict:
        """Insert a ledger entry and return the stored document (id as str)."""

    @abstractmethod
    def list_entries(
        self,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict]:
        """List ledger entries sorted newest-first with optional filters."""
