"""Vendors CRUD API."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from bson import ObjectId
from app.database import get_collection
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


def _fmt(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/")
async def list_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _: dict = Depends(require_role(["admin", "business"])),
):
    coll = get_collection("vendors")
    return [_fmt(d) for d in coll.find().skip(skip).limit(limit)]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreate,
    _: dict = Depends(require_role(["admin", "business"])),
):
    coll = get_collection("vendors")
    if body.email and coll.find_one({"email": body.email}):
        raise HTTPException(status_code=400, detail="Vendor with this email already exists")
    doc = {**body.dict(), "created_at": datetime.utcnow(), "updated_at": datetime.utcnow()}
    res = coll.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _fmt(doc)


@router.get("/{vendor_id}")
async def get_vendor(
    vendor_id: str,
    _: dict = Depends(require_role(["admin", "business"])),
):
    coll = get_collection("vendors")
    try:
        doc = coll.find_one({"_id": ObjectId(vendor_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    if not doc:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _fmt(doc)


@router.put("/{vendor_id}")
async def update_vendor(
    vendor_id: str,
    body: VendorUpdate,
    _: dict = Depends(require_role(["admin", "business"])),
):
    coll = get_collection("vendors")
    try:
        oid = ObjectId(vendor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.utcnow()
    res = coll.update_one({"_id": oid}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _fmt(coll.find_one({"_id": oid}))


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: str,
    _: dict = Depends(require_role(["admin"])),
):
    coll = get_collection("vendors")
    try:
        oid = ObjectId(vendor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    res = coll.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
