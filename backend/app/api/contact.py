"""Contact inquiry API."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from app.database import get_collection
from app.utils.rbac import require_role

router = APIRouter(prefix="/api/contact", tags=["Contact"])


class ContactInquiry(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=300)
    message: str = Field(..., min_length=1, max_length=5000)


class ContactInquiryUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(new|in_progress|resolved|closed)$")
    admin_notes: Optional[str] = None


def _fmt(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_inquiry(body: ContactInquiry):
    """Submit a contact inquiry (public endpoint)."""
    coll = get_collection("contact_inquiries")
    doc = {
        **body.model_dump(),
        "status": "new",
        "admin_notes": "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    res = coll.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _fmt(doc)


@router.get("/")
async def list_inquiries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    inquiry_status: Optional[str] = Query(None),
    _: dict = Depends(require_role(["admin"])),
):
    """List contact inquiries (admin only)."""
    coll = get_collection("contact_inquiries")
    query = {"status": inquiry_status} if inquiry_status else {}
    docs = list(coll.find(query).sort("created_at", -1).skip(skip).limit(limit))
    return [_fmt(d) for d in docs]


@router.get("/{inquiry_id}")
async def get_inquiry(
    inquiry_id: str,
    _: dict = Depends(require_role(["admin"])),
):
    """Get single inquiry detail (admin only)."""
    coll = get_collection("contact_inquiries")
    try:
        doc = coll.find_one({"_id": ObjectId(inquiry_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    if not doc:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return _fmt(doc)


@router.put("/{inquiry_id}")
async def update_inquiry(
    inquiry_id: str,
    body: ContactInquiryUpdate,
    _: dict = Depends(require_role(["admin"])),
):
    """Update inquiry status/notes (admin only)."""
    coll = get_collection("contact_inquiries")
    try:
        oid = ObjectId(inquiry_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.utcnow()
    res = coll.update_one({"_id": oid}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return _fmt(coll.find_one({"_id": oid}))
