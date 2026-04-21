"""MySQL-backed report repository."""
from __future__ import annotations

from datetime import datetime

from app.data.repositories.mysql_base import MySQLRepositoryBase
from app.domain.contracts.report_repository import ReportRepository


class MySQLReportRepository(MySQLRepositoryBase, ReportRepository):
    """MySQL implementation for reporting and analytics reads."""

    @staticmethod
    def _date_filter(start_date: datetime | None, end_date: datetime | None) -> dict:
        if not start_date and not end_date:
            return {}
        date_filter: dict = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        return {"created_at": date_filter}

    def list_orders(self, start_date: datetime | None = None, end_date: datetime | None = None) -> list[dict]:
        return self.find_many_docs(
            "orders",
            self._date_filter(start_date, end_date),
            order_by="created_at",
            descending=True,
        )

    def list_ledger_entries(
        self,
        category: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        query = self._date_filter(start_date, end_date)
        if category:
            query["category"] = category
        return self.find_many_docs("ledger", query, order_by="created_at", descending=True)

    def list_all_products(self) -> list[dict]:
        return self.find_many_docs("products", {})

    def list_customers(self) -> list[dict]:
        return self.find_many_docs("users", {"role": "customer"})

    def list_orders_by_customer_keys(self, customer_keys: list) -> list[dict]:
        if not customer_keys:
            return []
        return self.find_many_docs("orders", {"customer_id": {"$in": customer_keys}})

    def list_all_vendors(self) -> list[dict]:
        return self.find_many_docs("vendors", {})