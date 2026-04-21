"""SQL Server analytics repository — uses T-SQL aggregate queries (Phase 8).

All summaries push computation into T-SQL (COUNT/SUM/GROUP BY) so route
handlers receive pre-computed values and contain no aggregation logic.

Key T-SQL differences vs MySQL:
- Placeholder is ``?`` (not ``%s``)
- ``ISNULL(expr, 0)`` instead of ``COALESCE``
- Boolean columns are BIT — cast to int for SUM/CASE
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.data.mssql_client import mssql_connection
from app.data.repositories.mssql_base import MSSQLRepositoryBase
from app.domain.contracts.analytics_repository import AnalyticsRepository

_LOW_STOCK_THRESHOLD = 10


class MSSQLAnalyticsRepository(MSSQLRepositoryBase, AnalyticsRepository):
    """SQL Server implementation for pre-computed analytics summaries."""

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
            clauses.append(f"{col} >= ?")
            params.append(start_date)
        if end_date:
            clauses.append(f"{col} <= ?")
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
        """Execute an aggregate T-SQL query and return the single row as dict."""
        with mssql_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            if row is None or cursor.description is None:
                return {}
            cols = [col[0] for col in cursor.description]
            return dict(zip(cols, row))

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
            f"ISNULL(SUM(total), 0) AS total_sales, "
            f"ISNULL(SUM(total_gst), 0) AS total_gst "
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
        cat_where = f"category = ? AND {where}" if where != "1=1" else "category = ?"
        cat_params = ["purchases", *params]

        agg = self._scalar_execute(
            f"SELECT COUNT(*) AS total_purchases, "
            f"ISNULL(SUM(amount), 0) AS total_amount "
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

        ledger_agg = self._scalar_execute(
            f"SELECT "
            f"ISNULL(SUM(CASE WHEN category=N'sales' THEN amount ELSE 0 END), 0) AS total_revenue, "
            f"ISNULL(SUM(CASE WHEN category=N'purchases' THEN amount ELSE 0 END), 0) AS total_purchases "
            f"FROM ledger_entries WHERE {where}",
            params,
        )
        orders_agg = self._scalar_execute(
            f"SELECT ISNULL(SUM(total_gst), 0) AS total_gst FROM orders WHERE {where}",
            params,
        )

        total_revenue = float(ledger_agg.get("total_revenue", 0) or 0)
        total_purchases = float(ledger_agg.get("total_purchases", 0) or 0)
        total_gst = float(orders_agg.get("total_gst", 0) or 0)
        cogs = 0.0  # items not embedded in SQL Server orders table

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
            "ISNULL(SUM(CAST(stock_price AS FLOAT) * CAST(stock_quantity AS FLOAT)), 0) AS total_stock_value "
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
            "ISNULL(SUM(CAST(o.total AS FLOAT)), 0) AS total_spent "
            "FROM users u "
            "LEFT JOIN orders o ON o.customer_id = u.id "
            "WHERE u.role = ? "
            "GROUP BY u.id, u.username, u.email, u.full_name, u.role, u.phone, "
            "u.is_active, u.phone_verified, u.email_verified, u.created_at, u.updated_at"
        )
        with mssql_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, ("customer",))
            cols = [col[0] for col in cursor.description] if cursor.description else []
            rows = [dict(zip(cols, row)) for row in (cursor.fetchall() or [])]

        stats = []
        for row in rows:
            total_orders = int(row.pop("total_orders", 0) or 0)
            total_spent = float(row.pop("total_spent", 0) or 0)
            # Normalise BIT boolean columns.
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
