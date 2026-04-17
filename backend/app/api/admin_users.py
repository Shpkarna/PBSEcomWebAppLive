"""Admin user management CRUD."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from app.config import settings
from app.database import get_collection
from app.utils.rbac import require_role, VALID_ROLES
from app.utils.security import hash_password

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class UserCreateAdmin(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    role: str = "customer"
    is_active: bool = True
    phone_verified: bool = False
    email_verified: bool = False


class UserUpdateAdmin(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    phone_verified: Optional[bool] = None
    email_verified: Optional[bool] = None


def _fmt_user(u: dict) -> dict:
    u["id"] = str(u.pop("_id"))
    u.pop("password_hash", None)
    return u


import re as _re


@router.get("/users")
async def admin_list_users(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                           search: str = Query(None, max_length=100),
                           _: dict = Depends(require_role(["admin"]))):
    query: dict = {}
    if search and search.strip():
        pattern = _re.escape(search.strip())
        query["$or"] = [
            {"username": {"$regex": pattern, "$options": "i"}},
            {"email": {"$regex": pattern, "$options": "i"}},
            {"full_name": {"$regex": pattern, "$options": "i"}},
        ]
    docs = list(get_collection("users").find(query, {"password_hash": 0}).skip(skip).limit(limit))
    return [_fmt_user(d) for d in docs]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def admin_create_user(body: UserCreateAdmin, _: dict = Depends(require_role(["admin"]))):
    coll = get_collection("users")
    if coll.find_one({"username": body.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    if coll.find_one({"email": body.email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    if body.phone and coll.find_one({"phone": body.phone}):
        raise HTTPException(status_code=400, detail="Phone already exists")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
    now = datetime.utcnow()
    doc = {"username": body.username, "email": body.email,
           "password_hash": hash_password(body.password),
           "full_name": body.full_name or "", "phone": body.phone or "",
           "dob": body.dob or "", "sex": body.sex or "", 
           "marital_status": body.marital_status or "",
           "address": body.address or "", "role": body.role,
           "is_active": body.is_active,
           "phone_verified": False,
           "email_verified": False,
           "created_at": now, "updated_at": now}
    res = coll.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _fmt_user(doc)


@router.put("/users/{username}")
async def admin_update_user(username: str, body: UserUpdateAdmin,
                            _: dict = Depends(require_role(["admin"]))):
    if username == settings.admin_username:
        raise HTTPException(status_code=403, detail="Admin record is not editable")
    coll = get_collection("users")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if body.role and body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided")

    user = coll.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    requested_email = updates.get("email")
    if requested_email is not None and requested_email != user.get("email"):
        if coll.find_one({"email": requested_email, "username": {"$ne": username}}):
            raise HTTPException(status_code=400, detail="Email already exists")
        updates["email_verified"] = False

    requested_phone = updates.get("phone")
    if requested_phone is not None and requested_phone != user.get("phone"):
        if requested_phone and coll.find_one({"phone": requested_phone, "username": {"$ne": username}}):
            raise HTTPException(status_code=400, detail="Phone already exists")
        updates["phone_verified"] = False

    updates["updated_at"] = datetime.utcnow()
    res = coll.update_one({"username": username}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return _fmt_user(coll.find_one({"username": username}, {"password_hash": 0}))


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(username: str, _: dict = Depends(require_role(["admin"]))):
    if username == settings.admin_username:
        raise HTTPException(status_code=403, detail="Admin record cannot be deleted")
    if get_collection("users").delete_one({"username": username}).deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/users/{username}/assign-role")
async def admin_assign_customer_role(username: str, _: dict = Depends(require_role(["admin"]))):
    """
    Assign customer role to a user.
    Used after user completes phone verification during registration.
    """
    coll = get_collection("users")
    user = coll.find_one({"username": username})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user already has a role
    if user.get("role"):
        raise HTTPException(status_code=400, 
                            detail=f"User already has role '{user.get('role')}'")
    
    # Check if phone is verified (mandatory for registration)
    if not user.get("phone_verified"):
        raise HTTPException(status_code=400,
                            detail="User must complete phone verification before role assignment")
    
    # Assign customer role
    coll.update_one(
        {"username": username},
        {"$set": {"role": "customer", "updated_at": datetime.utcnow()}}
    )
    
    updated_user = coll.find_one({"username": username}, {"password_hash": 0})
    return {
        "message": f"Customer role assigned to user '{username}'",
        "user": _fmt_user(updated_user)
    }


@router.get("/unverified-users")
async def admin_list_unverified_users(skip: int = Query(0, ge=0), 
                                     limit: int = Query(50, ge=1, le=200),
                                     _: dict = Depends(require_role(["admin"]))):
    """
    List users who have completed phone verification but haven't been assigned a role yet.
    These are waiting for admin approval.
    """
    docs = list(get_collection("users").find(
        {"phone_verified": True, "role": None},
        {"password_hash": 0}
    ).skip(skip).limit(limit))
    return [_fmt_user(d) for d in docs]
