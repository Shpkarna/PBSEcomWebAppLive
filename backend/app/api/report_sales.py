"""Sales and purchase report routes."""
from fastapi import APIRouter, Depends, Query
from app.database import get_collection
from app.api.ledger import get_current_admin
from bson import ObjectId
from datetime import datetime

router = APIRouter(prefix="/api/reports", tags=["Reports & Ledger"])


def _sanitize(doc):
    """Convert ObjectId values to strings so dicts are JSON-safe."""
    if isinstance(doc, list):
        return [_sanitize(d) for d in doc]
    if isinstance(doc, dict):
        return {k: str(v) if isinstance(v, ObjectId) else _sanitize(v) for k, v in doc.items()}
    return doc


def _date_query(start_date, end_date):
    if not start_date and not end_date:
        return {}
    dq = {}
    if start_date:
        dq["$gte"] = datetime.fromisoformat(start_date)
    if end_date:
        dq["$lte"] = datetime.fromisoformat(end_date)
    return {"created_at": dq}


@router.get("/sales/")
async def get_sales_report(
    start_date: str = Query(None), end_date: str = Query(None),
    admin: str = Depends(get_current_admin),
):
    """Get sales report (Admin only)"""
    orders = list(get_collection("orders").find(_date_query(start_date, end_date)))
    total_sales = sum(o.get("total", 0) for o in orders)
    total_gst = sum(o.get("total_gst", 0) for o in orders)
    return {
        "period": f"{start_date} to {end_date}" if start_date or end_date else "All time",
        "total_orders": len(orders), "total_items_sold": sum(len(o.get("items", [])) for o in orders),
        "total_sales": total_sales, "total_gst_collected": total_gst,
        "average_order_value": total_sales / len(orders) if orders else 0, "orders": _sanitize(orders),
    }


@router.get("/purchases/")
async def get_purchase_report(
    start_date: str = Query(None), end_date: str = Query(None),
    admin: str = Depends(get_current_admin),
):
    """Get purchase report (Admin only)"""
    query = {"category": "purchases"}
    query.update(_date_query(start_date, end_date))
    purchases = list(get_collection("ledger").find(query))
    return {
        "period": f"{start_date} to {end_date}" if start_date or end_date else "All time",
        "total_purchases": len(purchases),
        "total_purchase_amount": sum(p.get("amount", 0) for p in purchases),
        "purchases": _sanitize(purchases),
    }


@router.get("/finances/")
async def get_company_finances(
    start_date: str = Query(None), end_date: str = Query(None),
    admin: str = Depends(get_current_admin),
):
    """Get company finances report (Admin only)"""
    query = _date_query(start_date, end_date)
    txns = list(get_collection("ledger").find(query))
    total_sales = sum(t.get("amount", 0) for t in txns if t.get("category") == "sales")
    total_purchases = sum(t.get("amount", 0) for t in txns if t.get("category") == "purchases")
    orders = list(get_collection("orders").find(query))
    total_gst = sum(o.get("total_gst", 0) for o in orders)
    cost = sum(
        i.get("stock_price", 0) * i.get("quantity", 0)
        for o in orders for i in o.get("items", [])
    )
    return {
        "period": f"{start_date} to {end_date}" if start_date or end_date else "All time",
        "total_revenue": total_sales, "total_purchases": total_purchases,
        "total_gst_collected": total_gst, "total_cost_of_goods": cost,
        "gross_profit": total_sales - cost, "net_profit": total_sales - total_purchases - cost,
    }
