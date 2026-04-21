"""
Role-based access control utilities.
"""
from datetime import datetime
from typing import Dict, List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.data.repository_providers import get_utility_repository
from app.models.enums import UserRole
from app.utils.security import decode_token, get_token_from_credentials, security

FUNCTIONALITIES: List[Dict[str, str]] = [
    {
        "code": "user_profile",
        "name": "User Profile",
        "description": "Access and manage personal profile page.",
    },
    {
        "code": "customer_purchase",
        "name": "Customer Purchase",
        "description": "User sign in, select product, checkout, and make payment.",
    },
    {
        "code": "inventory_manage",
        "name": "Inventory Management",
        "description": "Create product or update product stock.",
    },
]

DEFAULT_ROLE_MAPPINGS: Dict[str, List[str]] = {
    "user": ["user_profile"],
    "customer": ["user_profile", "customer_purchase"],
    "business": ["user_profile", "inventory_manage"],
    "vendor": ["user_profile", "inventory_manage"],
}

VALID_ROLES = [role.value for role in UserRole]


def ensure_default_role_mappings() -> None:
    """Ensure default role-functionality documents exist."""
    utility_repo = get_utility_repository()
    existing_roles = {doc.get("_id") for doc in utility_repo.list_role_permissions()}
    for role, functionalities in DEFAULT_ROLE_MAPPINGS.items():
        if role in existing_roles:
            continue
        utility_repo.update_role_permissions(role, functionalities, datetime.utcnow())


def get_role_mappings() -> Dict[str, List[str]]:
    """Get role mappings merged with defaults."""
    ensure_default_role_mappings()

    mappings: Dict[str, List[str]] = {role: funcs[:] for role, funcs in DEFAULT_ROLE_MAPPINGS.items()}
    for doc in get_utility_repository().list_role_permissions():
        mappings[doc["_id"]] = doc.get("functionalities", [])

    return mappings


def get_user_role(username: str) -> str:
    """Fetch effective role from user record."""
    utility_repo = get_utility_repository()
    mapped = utility_repo.find_user_role_mapping(username)
    if mapped and mapped.get("role") in VALID_ROLES:
        return mapped["role"]

    user = utility_repo.find_user({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user.get("role", "customer")


def get_role_functionalities(role: str) -> List[str]:
    """Get functionalities assigned to a role. Admin is always full access."""
    all_functionality_codes = [f["code"] for f in FUNCTIONALITIES]
    if role == "admin":
        return all_functionality_codes

    mappings = get_role_mappings()
    return mappings.get(role, [])


def get_current_user_context(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, str]:
    """Resolve authenticated user context from bearer token."""
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    role = get_user_role(username)
    return {"username": username, "role": role}


def require_role(allowed_roles: List[str]):
    """Dependency factory: require one of allowed roles, with admin override."""

    def _dependency(ctx: Dict[str, str] = Depends(get_current_user_context)) -> Dict[str, str]:
        if ctx["role"] == "admin":
            return ctx
        if ctx["role"] not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return ctx

    return _dependency


def require_functionality(functionality_code: str):
    """Dependency factory: require functionality mapped to user's role, with admin override."""

    def _dependency(ctx: Dict[str, str] = Depends(get_current_user_context)) -> Dict[str, str]:
        if ctx["role"] == "admin":
            return ctx

        role_functionalities = get_role_functionalities(ctx["role"])
        if functionality_code not in role_functionalities:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Functionality '{functionality_code}' is not allowed for role '{ctx['role']}'",
            )

        return ctx

    return _dependency
