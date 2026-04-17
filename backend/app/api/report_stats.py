"""Stock, customer, and vendor report routes."""
from fastapi import APIRouter, Depends
from app.database import get_collection
from app.api.ledger import get_current_admin
from bson import ObjectId

router = APIRouter(prefix="/api/reports", tags=["Reports & Ledger"])


def _sanitize(doc):
    """Convert ObjectId values to strings so dicts are JSON-safe."""
    if isinstance(doc, list):
        return [_sanitize(d) for d in doc]
    if isinstance(doc, dict):
        return {k: str(v) if isinstance(v, ObjectId) else _sanitize(v) for k, v in doc.items()}
    return doc


@router.get("/stock/")
async def get_stock_report(admin: str = Depends(get_current_admin)):
    """Get stock report (Admin only)"""
    products = list(get_collection("products").find())
    low = [p for p in products if p.get("stock_quantity", 0) < 10]
    out = [p for p in products if p.get("stock_quantity", 0) == 0]
    total_val = sum(p.get("stock_price", 0) * p.get("stock_quantity", 0) for p in products)
    return {
        "total_products": len(products), "low_stock_items": len(low),
        "out_of_stock_items": len(out), "total_stock_value": total_val,
        "low_stock": low, "out_of_stock": out,
    }


@router.get("/customers/")
async def get_customer_report(admin: str = Depends(get_current_admin)):
    """Get customer report (Admin only)"""
    customers = list(get_collection("users").find({"role": "customer"}))
    orders_col = get_collection("orders")
    stats = []
    for c in customers:
        customer_keys = {str(c["_id"])}
        if c.get("customer_id"):
            customer_keys.add(c["customer_id"])
        orders = list(orders_col.find({"customer_id": {"$in": list(customer_keys)}}))
        stats.append({"customer": _sanitize(c), "total_orders": len(orders),
                       "total_spent": sum(o.get("total", 0) for o in orders)})
    return {"total_customers": len(customers), "customers": stats}


@router.get("/vendors/")
async def get_vendor_report(admin: str = Depends(get_current_admin)):
    """Get vendor report (Admin only)"""
    vendors = list(get_collection("vendors").find())
    return {"total_vendors": len(vendors), "vendors": _sanitize(vendors)}
