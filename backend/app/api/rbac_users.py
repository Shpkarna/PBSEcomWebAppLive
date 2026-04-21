"""RBAC user-role assignment routes."""
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from app.data.repository_providers import get_utility_repository
from app.domain.contracts.utility_repository import UtilityRepository
from app.config import settings
from app.utils.logger import log_event
from app.utils.rbac import (
    VALID_ROLES,
    get_current_user_context,
    get_role_functionalities,
    require_role,
)

router = APIRouter(prefix="/api/rbac", tags=["RBAC"])


@router.get("/me")
async def get_my_access(ctx: Dict[str, str] = Depends(get_current_user_context)):
    """Return effective role and functionalities for the authenticated user."""
    return {
        "username": ctx["username"],
        "role": ctx["role"],
        "functionalities": get_role_functionalities(ctx["role"]),
    }


@router.get("/users")
async def list_users(
    _: Dict[str, str] = Depends(require_role(["admin"])),
    utility_repo: UtilityRepository = Depends(get_utility_repository),
):
    """List users and their current roles."""
    users = utility_repo.list_users({})
    return {"users": [
        {"id": u.get("id", str(u.get("_id", ""))), "username": u.get("username"), "email": u.get("email"),
         "role": u.get("role", "customer"), "is_active": u.get("is_active", True)}
        for u in users
    ]}


@router.put("/users/{username}/role")
async def update_user_role(
    username: str, new_role: str,
    ctx: Dict[str, str] = Depends(require_role(["admin"])),
    utility_repo: UtilityRepository = Depends(get_utility_repository),
):
    """Assign role to a user."""
    if username == settings.admin_username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin record is not editable")
    if new_role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    user = utility_repo.find_user({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    utility_repo.update_user({"username": username},
                             {"role": new_role, "updated_at": datetime.utcnow()})

    utility_repo.update_user_role_mapping(username, new_role, datetime.utcnow())

    log_event(
        "user_role_updated",
        user=ctx["username"],
        details={
            "target_user": username,
            "old_role": user.get("role", "customer"),
            "new_role": new_role,
        },
        path=f"/api/rbac/users/{username}/role",
    )
    return {"message": f"User {username} role updated to {new_role}"}


@router.put("/users/{username}/status")
async def update_user_status(
    username: str,
    is_active: bool,
    ctx: Dict[str, str] = Depends(require_role(["admin"])),
    utility_repo: UtilityRepository = Depends(get_utility_repository),
):
    """Enable or disable a user account."""
    if username == settings.admin_username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin record is not editable")

    user = utility_repo.find_user({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    utility_repo.update_user(
        {"username": username},
        {"is_active": is_active, "updated_at": datetime.utcnow()},
    )

    log_event(
        "user_enabled" if is_active else "user_disabled",
        user=ctx["username"],
        details={"target_user": username},
        path=f"/api/rbac/users/{username}/status",
    )

    return {
        "message": f"User {username} {'enabled' if is_active else 'disabled'}",
        "username": username,
        "is_active": is_active,
    }
