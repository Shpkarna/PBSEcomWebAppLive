"""MongoDB analytics repository — uses aggregation pipelines (Phase 8).

All summaries push computation into Mongo pipelines ($group, $sum, $cond,
$lookup) so route handlers receive pre-computed values and contain no
engine-specific aggregation logic.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId

from app.database import get_collection
from app.domain.contracts.analytics_repository import AnalyticsRepository

_LOW_STOCK_THRESHOLD = 10


class MongoAnalyticsRepository(AnalyticsRepository):
    """Mongo aggregation-pipeline implementation of AnalyticsRepository."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize(doc):
        if isinstance(doc, list):
            return [MongoAnalyticsRepository._sanitize(d) for d in doc]
        if isinstance(doc, dict):
            return {
                k: str(v) if isinstance(v, ObjectId) else MongoAnalyticsRepository._sanitize(v)
                for k, v in doc.items()
            }
        return doc

    @staticmethod
    def _period_str(start_date: Optional[datetime], end_date: Optional[datetime]) -> str:
        if start_date or end_date:
            s = str(start_date) if start_date else "?"
            e = str(end_date) if end_date else "?"
            return f"{s} to {e}"
        return "All time"

    def _date_match(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> dict:
        """Build a Mongo $match filter for created_at range."""
        cr: dict = {}
        if start_date:
            cr["$gte"] = start_date
        if end_date:
            cr["$lte"] = end_date
        return {"created_at": cr} if cr else {}

    # ------------------------------------------------------------------
    # sales_summary
    # ------------------------------------------------------------------

    def sales_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        match = self._date_match(start_date, end_date)

        # One aggregation pipeline for all numeric KPIs.
        pipeline: list[dict] = []
        if match:
            pipeline.append({"$match": match})
        pipeline.append({
            "$group": {
                "_id": None,
                "total_orders": {"$sum": 1},
                "total_sales": {"$sum": "$total"},
                "total_gst": {"$sum": "$total_gst"},
                "total_items": {
                    "$sum": {"$ifNull": [{"$size": {"$ifNull": ["$items", []]}}, 0]}
                },
            }
        })
        agg = list(get_collection("orders").aggregate(pipeline))
        row = agg[0] if agg else {}

        total_orders = int(row.get("total_orders", 0) or 0)
        total_sales = float(row.get("total_sales", 0) or 0)
        total_gst = float(row.get("total_gst", 0) or 0)
        total_items = int(row.get("total_items", 0) or 0)

        orders = self._sanitize(list(get_collection("orders").find(match)))

        return {
            "period": self._period_str(start_date, end_date),
            "total_orders": total_orders,
            "total_items_sold": total_items,
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
        query: dict = {"category": "purchases"}
        date_match = self._date_match(start_date, end_date)
        if date_match:
            query.update(date_match)

        pipeline = [{"$match": query}, {
            "$group": {
                "_id": None,
                "total_purchases": {"$sum": 1},
                "total_amount": {"$sum": "$amount"},
            }
        }]
        agg = list(get_collection("ledger").aggregate(pipeline))
        row = agg[0] if agg else {}

        purchases = self._sanitize(list(get_collection("ledger").find(query)))

        return {
            "period": self._period_str(start_date, end_date),
            "total_purchases": int(row.get("total_purchases", 0) or 0),
            "total_purchase_amount": float(row.get("total_amount", 0) or 0),
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
        date_match = self._date_match(start_date, end_date)

        # Revenue + GST + COGS from orders pipeline.
        orders_pipeline: list[dict] = []
        if date_match:
            orders_pipeline.append({"$match": date_match})
        orders_pipeline.append({
            "$group": {
                "_id": None,
                "total_gst": {"$sum": "$total_gst"},
                "cost_of_goods": {
                    "$sum": {
                        "$reduce": {
                            "input": {"$ifNull": ["$items", []]},
                            "initialValue": 0,
                            "in": {
                                "$add": [
                                    "$$value",
                                    {
                                        "$multiply": [
                                            {"$ifNull": ["$$this.stock_price", 0]},
                                            {"$ifNull": ["$$this.quantity", 0]},
                                        ]
                                    },
                                ]
                            },
                        }
                    }
                },
            }
        })
        orders_agg = list(get_collection("orders").aggregate(orders_pipeline))
        o_row = orders_agg[0] if orders_agg else {}

        # Revenue and purchases from ledger pipeline.
        ledger_pipeline: list[dict] = []
        if date_match:
            ledger_pipeline.append({"$match": date_match})
        ledger_pipeline.append({
            "$group": {
                "_id": "$category",
                "total": {"$sum": "$amount"},
            }
        })
        ledger_agg = list(get_collection("ledger").aggregate(ledger_pipeline))
        by_cat = {r["_id"]: float(r.get("total", 0) or 0) for r in ledger_agg}

        total_revenue = by_cat.get("sales", 0.0)
        total_purchases = by_cat.get("purchases", 0.0)
        total_gst = float(o_row.get("total_gst", 0) or 0)
        cogs = float(o_row.get("cost_of_goods", 0) or 0)

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
        pipeline = [{
            "$group": {
                "_id": None,
                "total_products": {"$sum": 1},
                "out_of_stock_items": {
                    "$sum": {"$cond": [{"$eq": ["$stock_quantity", 0]}, 1, 0]}
                },
                "low_stock_items": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$gt": ["$stock_quantity", 0]},
                                    {"$lt": ["$stock_quantity", _LOW_STOCK_THRESHOLD]},
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "total_stock_value": {
                    "$sum": {"$multiply": ["$stock_price", "$stock_quantity"]}
                },
            }
        }]
        agg = list(get_collection("products").aggregate(pipeline))
        row = agg[0] if agg else {}

        low = self._sanitize(list(get_collection("products").find(
            {"stock_quantity": {"$gt": 0, "$lt": _LOW_STOCK_THRESHOLD}}
        )))
        out = self._sanitize(list(get_collection("products").find({"stock_quantity": 0})))

        return {
            "total_products": int(row.get("total_products", 0) or 0),
            "low_stock_items": int(row.get("low_stock_items", 0) or 0),
            "out_of_stock_items": int(row.get("out_of_stock_items", 0) or 0),
            "total_stock_value": float(row.get("total_stock_value", 0) or 0),
            "low_stock": low,
            "out_of_stock": out,
        }

    # ------------------------------------------------------------------
    # customer_summary
    # ------------------------------------------------------------------

    def customer_summary(self) -> dict:
        """Single $lookup pipeline — no N+1 per-customer queries."""
        pipeline = [
            {"$match": {"role": "customer"}},
            {
                "$lookup": {
                    "from": "orders",
                    "let": {
                        "uid": {"$toString": "$_id"},
                        "cid": {"$ifNull": ["$customer_id", ""]},
                    },
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$or": [
                                        {"$eq": ["$customer_id", "$$uid"]},
                                        {"$eq": ["$customer_id", "$$cid"]},
                                    ]
                                }
                            }
                        },
                        {
                            "$group": {
                                "_id": None,
                                "total_orders": {"$sum": 1},
                                "total_spent": {"$sum": "$total"},
                            }
                        },
                    ],
                    "as": "_order_stats",
                }
            },
            {
                "$project": {
                    "_order_stats": 0,
                    "total_orders": {
                        "$ifNull": [{"$arrayElemAt": ["$_order_stats.total_orders", 0]}, 0]
                    },
                    "total_spent": {
                        "$ifNull": [{"$arrayElemAt": ["$_order_stats.total_spent", 0]}, 0.0]
                    },
                }
            },
        ]
        results = list(get_collection("users").aggregate(pipeline))
        stats = []
        for r in results:
            total_orders = int(r.pop("total_orders", 0) or 0)
            total_spent = float(r.pop("total_spent", 0) or 0)
            stats.append({
                "customer": self._sanitize(r),
                "total_orders": total_orders,
                "total_spent": total_spent,
            })
        return {"total_customers": len(stats), "customers": stats}

    # ------------------------------------------------------------------
    # vendor_summary
    # ------------------------------------------------------------------

    def vendor_summary(self) -> dict:
        vendors = self._sanitize(list(get_collection("vendors").find()))
        return {"total_vendors": len(vendors), "vendors": vendors}
