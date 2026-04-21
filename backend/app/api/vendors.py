"""Vendors CRUD API."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.utils.rbac import require_role

router = APIRouter(prefix="/api/vendors", tags=["Vendors"])


class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    bank_details: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    gst_number: Optional[str] = None
    bank_details: Optional[str] = None


@router.get("/")
async def list_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: dict = Depends(require_role(["admin", "business"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    return repo.list_vendors(skip, limit)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreate,
    _: dict = Depends(require_role(["admin", "business"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    if body.email and repo.find_vendor_by_email(body.email):
        raise HTTPException(status_code=400, detail="Vendor with this email already exists")
    doc = {**body.dict(), "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
    return repo.create_vendor(doc)


@router.get("/{vendor_id}")
async def get_vendor(
    vendor_id: str,
    _: dict = Depends(require_role(["admin", "business"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    doc = repo.get_vendor(vendor_id)
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid ID or vendor not found")
    return doc


@router.put("/{vendor_id}")
async def update_vendor(
    vendor_id: str,
    body: VendorUpdate,
    _: dict = Depends(require_role(["admin", "business"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.utcnow()
    if repo.update_vendor(vendor_id, updates) == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return repo.get_vendor(vendor_id)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: str,
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    if repo.delete_vendor(vendor_id) == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
