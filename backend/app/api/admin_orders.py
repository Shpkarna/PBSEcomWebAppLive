"""Admin order management routes."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.utils.rbac import require_role

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/orders")
async def admin_list_orders(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    order_status: Optional[str] = Query(None),
    _: dict = Depends(require_role(["admin", "business"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    query = {"status": order_status} if order_status else {}
    return repo.list_orders_filtered(query, skip, limit)


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
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """List all sales orders with server-side filters and paging."""
    docs, total = repo.search_sales_orders(
        order_id=order_id,
        order_number=order_number,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        skip=skip,
        limit=limit,
    )

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
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Update order status (Admin only)."""
    valid = ["pending", "confirmed", "processing", "shipped", "delivered",
             "cancelled", "return_requested", "returned"]
    if new_status not in valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid status. Must be one of: {', '.join(valid)}")
    matched = repo.update_order_status(order_id, new_status, datetime.utcnow())
    if not matched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {"message": f"Order status updated to {new_status}"}
