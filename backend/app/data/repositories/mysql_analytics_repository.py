"""MySQL analytics repository — uses SQL aggregate queries (Phase 8).

All summaries push computation into SQL (COUNT/SUM/GROUP BY) so route
handlers receive pre-computed values and contain no aggregation logic.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.data.mysql_client import mysql_connection
from app.data.repositories.mysql_base import MySQLRepositoryBase
from app.domain.contracts.analytics_repository import AnalyticsRepository

_LOW_STOCK_THRESHOLD = 10


class MySQLAnalyticsRepository(MySQLRepositoryBase, AnalyticsRepository):
    """MySQL implementation for pre-computed analytics summaries."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _period_str(start_date: Optional[datetime], end_date: Optional[datetime]) -> str:
        if start_date or end_date:
            s = str(start_date) if start_date else "?"
            e = str(end_date) if end_date else "?"
            return f"{s} to {e}"
        return "All time"

    def _date_where(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        col: str = "created_at",
    ) -> tuple[str, list[Any]]:
        """Return (WHERE clause fragment, params list) for a date range filter."""
        clauses: list[str] = []
        params: list[Any] = []
        if start_date:
            clauses.append(f"{col} >= %s")
            params.append(start_date)
        if end_date:
            clauses.append(f"{col} <= %s")
            params.append(end_date)
        return (" AND ".join(clauses) if clauses else "1=1"), params

    def _date_filter_doc(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> dict:
        """Return a mongo-style filter dict accepted by find_many_docs."""
        cr: dict = {}
        if start_date:
            cr["$gte"] = start_date
        if end_date:
            cr["$lte"] = end_date
        return {"created_at": cr} if cr else {}

    def _scalar_execute(self, sql: str, params: list[Any]) -> dict:
        """Execute an aggregate SQL query and return the single result row as dict."""
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                return dict(row) if row else {}

    # ------------------------------------------------------------------
    # sales_summary
    # ------------------------------------------------------------------

    def sales_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        where, params = self._date_where(start_date, end_date)

        agg = self._scalar_execute(
            f"SELECT COUNT(*) AS total_orders, "
            f"COALESCE(SUM(total), 0) AS total_sales, "
            f"COALESCE(SUM(total_gst), 0) AS total_gst "
            f"FROM orders WHERE {where}",
            params,
        )
        total_orders = int(agg.get("total_orders", 0) or 0)
        total_sales = float(agg.get("total_sales", 0) or 0)
        total_gst = float(agg.get("total_gst", 0) or 0)

        orders = self.find_many_docs(
            "orders",
            self._date_filter_doc(start_date, end_date),
            order_by="created_at",
            descending=True,
        )

        return {
            "period": self._period_str(start_date, end_date),
            "total_orders": total_orders,
            "total_items_sold": 0,  # items are not embedded in the SQL orders table
            "total_sales": total_sales,
            "total_gst_collected": total_gst,
            "average_order_value": total_sales / total_orders if total_orders else 0.0,
            "orders": orders,
        }

    # ------------------------------------------------------------------
    # purchase_summary
    # ------------------------------------------------------------------

    def purchase_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        where, params = self._date_where(start_date, end_date)
        # Category filter is always applied; append to existing WHERE.
        cat_where = f"category = %s AND {where}" if where != "1=1" else "category = %s"
        cat_params = ["purchases", *params]

        agg = self._scalar_execute(
            f"SELECT COUNT(*) AS total_purchases, "
            f"COALESCE(SUM(amount), 0) AS total_amount "
            f"FROM ledger_entries WHERE {cat_where}",
            cat_params,
        )
        filter_doc = {"category": "purchases"}
        filter_doc.update(self._date_filter_doc(start_date, end_date))
        purchases = self.find_many_docs(
            "ledger", filter_doc, order_by="created_at", descending=True
        )

        return {
            "period": self._period_str(start_date, end_date),
            "total_purchases": int(agg.get("total_purchases", 0) or 0),
            "total_purchase_amount": float(agg.get("total_amount", 0) or 0),
            "purchases": purchases,
        }

    # ------------------------------------------------------------------
    # finance_summary
    # ------------------------------------------------------------------

    def finance_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        where, params = self._date_where(start_date, end_date)

        # Aggregate revenue/purchases from ledger in a single pass.
        ledger_agg = self._scalar_execute(
            f"SELECT "
            f"COALESCE(SUM(CASE WHEN category='sales' THEN amount ELSE 0 END), 0) AS total_revenue, "
            f"COALESCE(SUM(CASE WHEN category='purchases' THEN amount ELSE 0 END), 0) AS total_purchases "
            f"FROM ledger_entries WHERE {where}",
            params,
        )
        # Aggregate GST from orders.
        orders_agg = self._scalar_execute(
            f"SELECT COALESCE(SUM(total_gst), 0) AS total_gst FROM orders WHERE {where}",
            params,
        )

        total_revenue = float(ledger_agg.get("total_revenue", 0) or 0)
        total_purchases = float(ledger_agg.get("total_purchases", 0) or 0)
        total_gst = float(orders_agg.get("total_gst", 0) or 0)
        cogs = 0.0  # items not embedded in SQL orders table

        return {
            "period": self._period_str(start_date, end_date),
            "total_revenue": total_revenue,
            "total_purchases": total_purchases,
            "total_gst_collected": total_gst,
            "total_cost_of_goods": cogs,
            "gross_profit": total_revenue - cogs,
            "net_profit": total_revenue - total_purchases - cogs,
        }

    # ------------------------------------------------------------------
    # stock_summary
    # ------------------------------------------------------------------

    def stock_summary(self) -> dict:
        agg = self._scalar_execute(
            "SELECT "
            "COUNT(*) AS total_products, "
            f"SUM(CASE WHEN stock_quantity = 0 THEN 1 ELSE 0 END) AS out_of_stock_items, "
            f"SUM(CASE WHEN stock_quantity > 0 AND stock_quantity < {_LOW_STOCK_THRESHOLD} THEN 1 ELSE 0 END) AS low_stock_items, "
            "COALESCE(SUM(stock_price * stock_quantity), 0) AS total_stock_value "
            "FROM products",
            [],
        )

        low = self.find_many_docs(
            "products",
            {"stock_quantity": {"$gt": 0, "$lt": _LOW_STOCK_THRESHOLD}},
        )
        out = self.find_many_docs("products", {"stock_quantity": 0})

        return {
            "total_products": int(agg.get("total_products", 0) or 0),
            "low_stock_items": int(agg.get("low_stock_items", 0) or 0),
            "out_of_stock_items": int(agg.get("out_of_stock_items", 0) or 0),
            "total_stock_value": float(agg.get("total_stock_value", 0) or 0),
            "low_stock": low,
            "out_of_stock": out,
        }

    # ------------------------------------------------------------------
    # customer_summary  — solved with a LEFT JOIN (no N+1)
    # ------------------------------------------------------------------

    def customer_summary(self) -> dict:
        sql = (
            "SELECT u.id, u.username, u.email, u.full_name, u.role, u.phone, "
            "u.is_active, u.phone_verified, u.email_verified, u.created_at, u.updated_at, "
            "COUNT(o.id) AS total_orders, "
            "COALESCE(SUM(o.total), 0) AS total_spent "
            "FROM users u "
            "LEFT JOIN orders o ON o.customer_id = u.id "
            "WHERE u.role = %s "
            "GROUP BY u.id, u.username, u.email, u.full_name, u.role, u.phone, "
            "u.is_active, u.phone_verified, u.email_verified, u.created_at, u.updated_at"
        )
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, ("customer",))
                rows = cur.fetchall() or []

        stats = []
        for row in rows:
            row = dict(row)
            total_orders = int(row.pop("total_orders", 0) or 0)
            total_spent = float(row.pop("total_spent", 0) or 0)
            # Normalise bool columns.
            for col in ("is_active", "phone_verified", "email_verified"):
                if col in row:
                    row[col] = bool(row[col])
            row.setdefault("_id", str(row.get("id", "")))
            stats.append({
                "customer": row,
                "total_orders": total_orders,
                "total_spent": total_spent,
            })
        return {"total_customers": len(stats), "customers": stats}

    # ------------------------------------------------------------------
    # vendor_summary
    # ------------------------------------------------------------------

    def vendor_summary(self) -> dict:
        vendors = self.find_many_docs("vendors", {})
        return {"total_vendors": len(vendors), "vendors": vendors}
