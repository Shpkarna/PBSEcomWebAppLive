"""Repository contract for analytics and report data access.

Phase 2 added this contract so report routes consume named abstract operations
instead of raw MongoDB collections via the order/cart gateway passthrough.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class ReportRepository(ABC):
    """Storage-agnostic gateway for reporting and analytics queries."""

    @abstractmethod
    def list_orders(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict]:
        """Return orders with optional date range filter."""

    @abstractmethod
    def list_ledger_entries(
        self,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict]:
        """Return ledger entries with optional category and date range filter."""

    @abstractmethod
    def list_all_products(self) -> list[dict]:
        """Return all products for stock reporting."""

    @abstractmethod
    def list_customers(self) -> list[dict]:
        """Return all users with role 'customer'."""

    @abstractmethod
    def list_orders_by_customer_keys(self, customer_keys: list) -> list[dict]:
        """Return orders whose customer_id matches any of the given keys."""

    @abstractmethod
    def list_all_vendors(self) -> list[dict]:
        """Return all vendor documents."""
