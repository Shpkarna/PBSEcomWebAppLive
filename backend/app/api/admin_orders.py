"""Admin order management routes."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId
from app.database import get_collection
from app.utils.rbac import require_role

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/orders")
async def admin_list_orders(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    order_status: Optional[str] = Query(None),
    _: dict = Depends(require_role(["admin", "business"])),
):
    coll = get_collection("orders")
    query = {"status": order_status} if order_status else {}
    docs = list(coll.find(query).sort("created_at", -1).skip(skip).limit(limit))
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs


@router.get("/orders/sales")
async def admin_list_sales_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    order_id: Optional[str] = Query(None),
    order_number: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    amount_min: Optional[float] = Query(None, ge=0),
    amount_max: Optional[float] = Query(None, ge=0),
    _: dict = Depends(require_role(["admin", "business"])),
):
    """List all sales orders with server-side filters and paging."""
    coll = get_collection("orders")

    match_query = {}
    if date_from or date_to:
        created_range = {}
        if date_from:
            created_range["$gte"] = date_from
        if date_to:
            created_range["$lte"] = date_to
        match_query["created_at"] = created_range

    if amount_min is not None or amount_max is not None:
        amount_range = {}
        if amount_min is not None:
            amount_range["$gte"] = amount_min
        if amount_max is not None:
            amount_range["$lte"] = amount_max
        match_query["total"] = amount_range

    pipeline = [{
        "$addFields": {
            "id": {"$toString": "$_id"},
        }
    }]

    if order_id:
        pipeline.append({
            "$match": {
                "$or": [
                    {"id": {"$regex": order_id, "$options": "i"}},
                    {"order_number": {"$regex": order_id, "$options": "i"}},
                ]
            }
        })

    if order_number:
        pipeline.append({
            "$match": {
                "order_number": {"$regex": order_number, "$options": "i"}
            }
        })

    if match_query:
        pipeline.append({"$match": match_query})

    total_pipeline = pipeline + [{"$count": "count"}]
    total_result = list(coll.aggregate(total_pipeline))
    total = total_result[0]["count"] if total_result else 0

    result_pipeline = pipeline + [
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
    ]

    docs = list(coll.aggregate(result_pipeline))
    for d in docs:
        d.pop("_id", None)

    return {
        "items": docs,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.put("/orders/{order_id}/status")
async def admin_update_order_status(
    order_id: str,
    new_status: str = Query(...),
    _: dict = Depends(require_role(["admin"])),
):
    """Update order status (Admin only)."""
    valid = ["pending", "confirmed", "processing", "shipped", "delivered",
             "cancelled", "return_requested", "returned"]
    if new_status not in valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid status. Must be one of: {', '.join(valid)}")
    orders_col = get_collection("orders")
    try:
        order_oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID")

    result = orders_col.update_one(
        {"_id": order_oid},
        {"$set": {"status": new_status, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {"message": f"Order status updated to {new_status}"}
