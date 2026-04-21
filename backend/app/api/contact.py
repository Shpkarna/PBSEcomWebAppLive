"""Contact inquiry API."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
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


@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_inquiry(
    body: ContactInquiry,
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Submit a contact inquiry (public endpoint)."""
    doc = {
        **body.model_dump(),
        "status": "new",
        "admin_notes": "",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    return repo.create_contact_inquiry(doc)


@router.get("/")
async def list_inquiries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    inquiry_status: Optional[str] = Query(None),
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """List contact inquiries (admin only)."""
    return repo.list_contact_inquiries(skip, limit, inquiry_status)


@router.get("/{inquiry_id}")
async def get_inquiry(
    inquiry_id: str,
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Get single inquiry detail (admin only)."""
    doc = repo.get_contact_inquiry(inquiry_id)
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid ID or inquiry not found")
    return doc


@router.put("/{inquiry_id}")
async def update_inquiry(
    inquiry_id: str,
    body: ContactInquiryUpdate,
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Update inquiry status/notes (admin only)."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.utcnow()
    if repo.update_contact_inquiry(inquiry_id, updates) == 0:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return repo.get_contact_inquiry(inquiry_id)
