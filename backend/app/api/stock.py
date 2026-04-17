"""Stock Ledger API — view and add stock movements."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from bson import ObjectId
from app.database import get_collection
from app.utils.rbac import require_role, require_functionality

router = APIRouter(prefix="/api/stock", tags=["Stock Ledger"])


class StockEntryCreate(BaseModel):
    product_id: str
    transaction_type: str = Field(..., pattern="^(inbound|outbound|adjustment)$")
    quantity: int = Field(..., ne=0)
    reference: Optional[str] = None
    notes: Optional[str] = None


def _fmt(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/")
async def list_stock_ledger(
    product_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: dict = Depends(require_role(["admin", "business", "vendor"])),
):
    coll = get_collection("stock_ledger")
    query = {}
    if product_id:
        query["product_id"] = product_id
    docs = list(coll.find(query).sort("created_at", -1).skip(skip).limit(limit))
    return [_fmt(d) for d in docs]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_stock_entry(
    body: StockEntryCreate,
    ctx: dict = Depends(require_functionality("inventory_manage")),
):
    prods = get_collection("products")
    try:
        prod = prods.find_one({"_id": ObjectId(body.product_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product ID")
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    delta = body.quantity if body.transaction_type == "inbound" else -body.quantity
    new_qty = prod.get("stock_quantity", 0) + delta
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock for outbound")

    prods.update_one(
        {"_id": ObjectId(body.product_id)},
        {"$set": {"stock_quantity": new_qty, "updated_at": datetime.utcnow()}},
    )

    coll = get_collection("stock_ledger")
    doc = {
        **body.dict(),
        "adjusted_quantity": new_qty,
        "created_by": ctx["username"],
        "created_at": datetime.utcnow(),
    }
    res = coll.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _fmt(doc)


@router.get("/{entry_id}")
async def get_stock_entry(
    entry_id: str,
    _: dict = Depends(require_role(["admin", "business"])),
):
    coll = get_collection("stock_ledger")
    try:
        doc = coll.find_one({"_id": ObjectId(entry_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    if not doc:
        raise HTTPException(status_code=404, detail="Entry not found")
    return _fmt(doc)
