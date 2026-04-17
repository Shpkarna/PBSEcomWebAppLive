"""Ledger API routes."""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from app.database import get_collection
from app.schemas.schemas import LedgerEntryBase, LedgerEntryResponse
from app.utils.security import decode_token, get_token_from_credentials, security
from datetime import datetime

router = APIRouter(prefix="/api/reports", tags=["Reports & Ledger"])


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return payload.get("sub")


@router.post("/ledger/entry", response_model=LedgerEntryResponse)
async def add_ledger_entry(entry: LedgerEntryBase, admin: str = Depends(get_current_admin)):
    """Add ledger entry (Admin only)"""
    ledger_col = get_collection("ledger")
    entry_dict = entry.model_dump()
    entry_dict["created_at"] = datetime.utcnow()
    result = ledger_col.insert_one(entry_dict)
    entry_dict["_id"] = result.inserted_id
    return LedgerEntryResponse(**entry_dict)


@router.get("/ledger/", response_model=list[LedgerEntryResponse])
async def get_ledger_entries(
    category: str = Query(None), start_date: str = Query(None),
    end_date: str = Query(None), admin: str = Depends(get_current_admin),
):
    """Get ledger entries (Admin only)"""
    ledger_col = get_collection("ledger")
    query = {}
    if category:
        query["category"] = category
    if start_date or end_date:
        dq = {}
        if start_date:
            dq["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            dq["$lte"] = datetime.fromisoformat(end_date)
        query["created_at"] = dq
    entries = list(ledger_col.find(query).sort("created_at", -1))
    return [LedgerEntryResponse(**e) for e in entries]
