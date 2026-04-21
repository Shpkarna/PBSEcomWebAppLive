"""Repository contract for analytics aggregations (Phase 8).

Analytics operations return fully pre-computed summary dicts so that API route
handlers contain zero engine-specific aggregation logic.  Each engine
implementation pushes the computation into the database (Mongo aggregation
pipeline, SQL GROUP BY / SUM) rather than fetching raw rows and summing in
Python at the application tier.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class AnalyticsRepository(ABC):
    """Storage-agnostic gateway for pre-computed analytics summaries."""

    # ------------------------------------------------------------------
    # report_sales endpoints
    # ------------------------------------------------------------------

    @abstractmethod
    def sales_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Return pre-computed sales KPIs plus the matching order list.

        Keys: period, total_orders, total_items_sold, total_sales,
              total_gst_collected, average_order_value, orders.
        """

    @abstractmethod
    def purchase_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Return pre-computed purchase KPIs plus the matching ledger list.

        Keys: period, total_purchases, total_purchase_amount, purchases.
        """

    @abstractmethod
    def finance_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Return pre-computed P&L summary.

        Keys: period, total_revenue, total_purchases, total_gst_collected,
              total_cost_of_goods, gross_profit, net_profit.
        """

    # ------------------------------------------------------------------
    # report_stats endpoints
    # ------------------------------------------------------------------

    @abstractmethod
    def stock_summary(self) -> dict:
        """Return pre-computed stock KPIs plus low/out-of-stock product lists.

        Keys: total_products, low_stock_items, out_of_stock_items,
              total_stock_value, low_stock, out_of_stock.
        """

    @abstractmethod
    def customer_summary(self) -> dict:
        """Return per-customer order count and spend; no N+1 in implementations.

        Keys: total_customers, customers (list of {customer, total_orders, total_spent}).
        """

    @abstractmethod
    def vendor_summary(self) -> dict:
        """Return all vendors with count.

        Keys: total_vendors, vendors.
        """
