"""RBAC role-to-functionality mapping routes."""
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_collection
from app.utils.rbac import (
    FUNCTIONALITIES, VALID_ROLES, ensure_default_role_mappings,
    get_role_mappings, require_role,
)

router = APIRouter(prefix="/api/rbac", tags=["RBAC"])
VALID_FUNCTIONALITIES = {f["code"] for f in FUNCTIONALITIES}


@router.get("/functionalities")
async def list_functionalities(_: Dict[str, str] = Depends(require_role(["admin"]))):
    """List all available functionalities."""
    return FUNCTIONALITIES


@router.get("/roles")
async def list_role_mappings(_: Dict[str, str] = Depends(require_role(["admin"]))):
    """List role to functionality mappings."""
    ensure_default_role_mappings()
    return {"roles": [{"role": r, "functionalities": f} for r, f in get_role_mappings().items()]}


@router.get("/valid-roles")
async def list_valid_roles(_: Dict[str, str] = Depends(require_role(["admin"]))):
    """List valid user roles from backend role enum/source of truth."""
    return {"roles": VALID_ROLES}


@router.put("/roles/{role_name}/functionalities")
async def update_role_mapping(
    role_name: str, functionalities: List[str],
    _: Dict[str, str] = Depends(require_role(["admin"])),
):
    """Update role to functionality mapping."""
    if role_name not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if role_name == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Admin access is always full and cannot be restricted")
    invalid = [f for f in functionalities if f not in VALID_FUNCTIONALITIES]
    if invalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid functionalities: {', '.join(invalid)}")

    role_perms = get_collection("role_permissions")
    rfm = get_collection("role_functionality_mappings")
    role_perms.update_one({"_id": role_name},
                          {"$set": {"functionalities": functionalities, "updated_at": datetime.utcnow()}},
                          upsert=True)
    rfm.delete_many({"role": role_name})
    if functionalities:
        rfm.insert_many([{"role": role_name, "functionality_code": c, "created_at": datetime.utcnow()}
                         for c in functionalities])
    return {"message": "Role mapping updated", "role": role_name, "functionalities": functionalities}
