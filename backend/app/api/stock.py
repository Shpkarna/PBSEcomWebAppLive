"""Stock Ledger API — view and add stock movements."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.utils.rbac import require_role, require_functionality

router = APIRouter(prefix="/api/stock", tags=["Stock Ledger"])


class StockEntryCreate(BaseModel):
    product_id: str
    transaction_type: str = Field(..., pattern="^(inbound|outbound|adjustment)$")
    quantity: int = Field(..., ne=0)
    reference: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def list_stock_ledger(
    product_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: dict = Depends(require_role(["admin", "business", "vendor"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    return repo.list_stock_ledger(product_id, skip, limit)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_stock_entry(
    body: StockEntryCreate,
    ctx: dict = Depends(require_functionality("inventory_manage")),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    prod = repo.find_product_by_id(body.product_id)
    if not prod:
        raise HTTPException(status_code=400, detail="Invalid product ID or product not found")

    delta = body.quantity if body.transaction_type == "inbound" else -body.quantity
    new_qty = prod.get("stock_quantity", 0) + delta
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock for outbound")

    repo.update_product_stock(body.product_id, new_qty)

    doc = {
        **body.dict(),
        "adjusted_quantity": new_qty,
        "created_by": ctx["username"],
        "created_at": datetime.utcnow(),
    }
    return repo.add_stock_entry(doc)


@router.get("/{entry_id}")
async def get_stock_entry(
    entry_id: str,
    _: dict = Depends(require_role(["admin", "business"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    doc = repo.get_stock_entry(entry_id)
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid ID or entry not found")
    return doc
