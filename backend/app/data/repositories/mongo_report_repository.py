"""MongoDB-backed report repository."""
from bson import ObjectId

from app.database import get_collection
from app.domain.contracts.report_repository import ReportRepository


class MongoReportRepository(ReportRepository):
    """Mongo implementation for analytics and report queries."""

    @staticmethod
    def _sanitize(doc):
        if isinstance(doc, list):
            return [MongoReportRepository._sanitize(d) for d in doc]
        if isinstance(doc, dict):
            return {
                k: str(v) if isinstance(v, ObjectId) else MongoReportRepository._sanitize(v)
                for k, v in doc.items()
            }
        return doc

    def list_orders(self, start_date=None, end_date=None) -> list[dict]:
        query: dict = {}
        if start_date or end_date:
            created_range: dict = {}
            if start_date:
                created_range["$gte"] = start_date
            if end_date:
                created_range["$lte"] = end_date
            query["created_at"] = created_range
        docs = list(get_collection("orders").find(query))
        return self._sanitize(docs)

    def list_ledger_entries(self, category=None, start_date=None, end_date=None) -> list[dict]:
        query: dict = {}
        if category:
            query["category"] = category
        if start_date or end_date:
            created_range: dict = {}
            if start_date:
                created_range["$gte"] = start_date
            if end_date:
                created_range["$lte"] = end_date
            query["created_at"] = created_range
        docs = list(get_collection("ledger").find(query))
        return self._sanitize(docs)

    def list_all_products(self) -> list[dict]:
        docs = list(get_collection("products").find())
        return self._sanitize(docs)

    def list_customers(self) -> list[dict]:
        docs = list(get_collection("users").find({"role": "customer"}))
        return self._sanitize(docs)

    def list_orders_by_customer_keys(self, customer_keys: list) -> list[dict]:
        docs = list(get_collection("orders").find({"customer_id": {"$in": customer_keys}}))
        return self._sanitize(docs)

    def list_all_vendors(self) -> list[dict]:
        docs = list(get_collection("vendors").find())
        return self._sanitize(docs)
