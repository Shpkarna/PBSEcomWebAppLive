"""Categories CRUD API."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.utils.rbac import require_role

router = APIRouter(prefix="/api/categories", tags=["Categories"])

DISCOUNT_PERCENTAGE = "Discount percentage"
DISCOUNT_AMOUNT = "Discount amount"
VALID_DISCOUNT_TYPES = {DISCOUNT_PERCENTAGE, DISCOUNT_AMOUNT}


def _validate_discount_fields(discount_type: Optional[str], discount_value: Optional[float]) -> None:
    if discount_type is None and discount_value is None:
        return
    if discount_type not in VALID_DISCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="Discount must be either 'Discount percentage' or 'Discount amount'")
    if discount_value is None:
        raise HTTPException(status_code=400, detail="Discount value is required when discount type is set")
    if discount_type == DISCOUNT_PERCENTAGE and (discount_value < 0 or discount_value > 100):
        raise HTTPException(status_code=400, detail="Discount percentage must be between 0 and 100")
    if discount_type == DISCOUNT_AMOUNT and discount_value < 0:
        raise HTTPException(status_code=400, detail="Discount amount must be 0 or greater")


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None


@router.get("/")
async def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    return repo.list_categories(skip, limit)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    _: dict = Depends(require_role(["admin", "business"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    if repo.find_category_by_name(body.name):
        raise HTTPException(status_code=400, detail="Category already exists")
    _validate_discount_fields(body.discount_type, body.discount_value)
    doc = {**body.dict(), "created_at": datetime.utcnow()}
    return repo.create_category(doc)


@router.get("/{cat_id}")
async def get_category(cat_id: str, repo: OrderCartRepository = Depends(get_order_cart_repository)):
    doc = repo.get_category(cat_id)
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid ID or category not found")
    return doc


@router.put("/{cat_id}")
async def update_category(
    cat_id: str,
    body: CategoryUpdate,
    _: dict = Depends(require_role(["admin", "business"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    current = repo.get_category(cat_id)
    if not current:
        raise HTTPException(status_code=404, detail="Category not found")

    effective_discount_type = updates.get("discount_type", current.get("discount_type"))
    effective_discount_value = updates.get("discount_value", current.get("discount_value"))
    _validate_discount_fields(effective_discount_type, effective_discount_value)

    updates["updated_at"] = datetime.utcnow()
    if repo.update_category(cat_id, updates) == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return repo.get_category(cat_id)


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    cat_id: str,
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    if repo.delete_category(cat_id) == 0:
        raise HTTPException(status_code=404, detail="Category not found")
