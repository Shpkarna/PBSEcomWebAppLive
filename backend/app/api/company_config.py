"""Company Configuration API (admin-only).

Stores site-wide settings in MongoDB collection `company_config`.
Currently manages:
  - MSG91 SMS credentials (authkey, template_id, sender_id)

Pattern mirrors payment_gateways.py: DB values are loaded into runtime
settings at startup so no restart is required after a UI save.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from fastapi import HTTPException, status

from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.utils.rbac import require_role
from app.config import settings

router = APIRouter(prefix="/api/admin/company-config", tags=["Company Config"])
public_router = APIRouter(prefix="/api/public", tags=["Public"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MSG91ConfigRequest(BaseModel):
    authkey: str = ""
    template_id: str = ""
    sender_id: Optional[str] = Field(default="AIESHP", min_length=1)
    enable_mobile_otp_verification: bool = True


class MSG91ConfigResponse(BaseModel):
    authkey: str
    template_id: str
    sender_id: str
    enable_mobile_otp_verification: bool = True


class MiscConfigRequest(BaseModel):
    enable_email_verification: bool = False
    company_name: str = ""


class MiscConfigResponse(BaseModel):
    enable_email_verification: bool = False
    company_name: str = ""


class CompanyInfoResponse(BaseModel):
    company_name: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_config(repo: OrderCartRepository, config_id: str):
    return repo.find_company_config(config_id)


def _upsert_config(repo: OrderCartRepository, config_id: str, data: dict):
    return repo.upsert_company_config(config_id, data)


def load_company_config_into_settings():
    """Load company configuration from DB into runtime settings at startup."""
    repo = get_order_cart_repository()
    doc = repo.find_company_config("msg91")
    if doc:
        authkey = doc.get("authkey", "").strip()
        template_id = doc.get("template_id", "").strip()
        sender_id = doc.get("sender_id", "").strip()
        enable_mobile_otp_verification = bool(doc.get("enable_mobile_otp_verification", True))
        if authkey:
            settings.msg91_authkey = authkey
        if template_id:
            settings.msg91_template_id = template_id
        if sender_id:
            settings.msg91_sender_id = sender_id
        settings.enable_mobile_otp_verification = enable_mobile_otp_verification

    misc_doc = repo.find_company_config("misc")
    if misc_doc:
        settings.enable_email_verification = bool(misc_doc.get("enable_email_verification", False))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/msg91", response_model=MSG91ConfigResponse)
async def get_msg91_config(
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Return stored MSG91 configuration (admin only)."""
    doc = _find_config(repo, "msg91")
    if doc:
        return MSG91ConfigResponse(
            authkey=doc.get("authkey", ""),
            template_id=doc.get("template_id", ""),
            sender_id=doc.get("sender_id", settings.msg91_sender_id),
            enable_mobile_otp_verification=bool(doc.get("enable_mobile_otp_verification", settings.enable_mobile_otp_verification)),
        )
    return MSG91ConfigResponse(
        authkey=settings.msg91_authkey,
        template_id=settings.msg91_template_id,
        sender_id=settings.msg91_sender_id,
        enable_mobile_otp_verification=settings.enable_mobile_otp_verification,
    )


@router.put("/msg91", response_model=dict)
async def update_msg91_config(
    body: MSG91ConfigRequest,
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Persist MSG91 credentials and update runtime settings immediately (admin only)."""
    if body.enable_mobile_otp_verification and (not body.authkey.strip() or not body.template_id.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="When mobile OTP verification is enabled, Auth Key and Template ID are required.",
        )

    sender = (body.sender_id or "AIESHP").strip()
    _upsert_config(repo, "msg91", {
        "configId": "msg91",
        "authkey": body.authkey.strip(),
        "template_id": body.template_id.strip(),
        "sender_id": sender,
        "enable_mobile_otp_verification": bool(body.enable_mobile_otp_verification),
    })
    settings.msg91_authkey = body.authkey.strip()
    settings.msg91_template_id = body.template_id.strip()
    settings.msg91_sender_id = sender
    settings.enable_mobile_otp_verification = bool(body.enable_mobile_otp_verification)
    return {"message": "MSG91 configuration updated successfully"}


@router.get("/misc", response_model=MiscConfigResponse)
async def get_misc_config(
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Return miscellaneous company settings (admin only)."""
    doc = _find_config(repo, "misc")
    if doc:
        return MiscConfigResponse(
            enable_email_verification=bool(doc.get("enable_email_verification", settings.enable_email_verification)),
            company_name=doc.get("company_name", ""),
        )
    return MiscConfigResponse(enable_email_verification=settings.enable_email_verification)


@router.put("/misc", response_model=dict)
async def update_misc_config(
    body: MiscConfigRequest,
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Persist miscellaneous company settings and update runtime values (admin only)."""
    _upsert_config(repo, "misc", {
        "configId": "misc",
        "enable_email_verification": bool(body.enable_email_verification),
        "company_name": body.company_name.strip(),
    })
    settings.enable_email_verification = bool(body.enable_email_verification)
    return {"message": "Misc configuration updated successfully"}


@public_router.get("/company-info", response_model=CompanyInfoResponse)
async def get_company_info(repo: OrderCartRepository = Depends(get_order_cart_repository)):
    """Return the company name for display in client apps. No authentication required."""
    doc = _find_config(repo, "misc")
    name = (doc.get("company_name", "") if doc else "").strip()
    return CompanyInfoResponse(company_name=name or "Our Company")
