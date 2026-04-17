"""Payment Gateway configuration API (admin-only).

Collection: payment_gateways
ID field:   gatewayId  (e.g. "razorpay")
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.database import get_collection
from app.utils.rbac import require_role
from app.config import settings

router = APIRouter(prefix="/api/admin/payment-gateways", tags=["Payment Gateways"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RazorpayConfigRequest(BaseModel):
    key_id: str
    key_secret: str


class RazorpayConfigResponse(BaseModel):
    gatewayId: str
    key_id: str
    key_secret: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col():
    return get_collection("payment_gateways")


def load_gateway_settings_into_config():
    """Load payment gateway credentials from DB and update runtime settings.

    Called at application startup so the API always uses the DB values when
    they exist, falling back to whatever is in config.py / .env.
    """
    doc = _col().find_one({"gatewayId": "razorpay"})
    if doc:
        key_id = doc.get("key_id", "").strip()
        key_secret = doc.get("key_secret", "").strip()
        if key_id:
            settings.razorpay_key_id = key_id
        if key_secret:
            settings.razorpay_key_secret = key_secret


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/razorpay", response_model=RazorpayConfigResponse)
async def get_razorpay_config(_: dict = Depends(require_role(["admin"]))):
    """Return the stored Razorpay configuration (admin only)."""
    doc = _col().find_one({"gatewayId": "razorpay"})
    if doc:
        return RazorpayConfigResponse(
            gatewayId="razorpay",
            key_id=doc.get("key_id", ""),
            key_secret=doc.get("key_secret", ""),
        )
    # Fallback: return what is in runtime settings (seeded from config/env)
    return RazorpayConfigResponse(
        gatewayId="razorpay",
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
    )


@router.put("/razorpay", response_model=dict)
async def update_razorpay_config(
    body: RazorpayConfigRequest,
    _: dict = Depends(require_role(["admin"])),
):
    """Persist Razorpay Key ID and Key Secret (admin only).

    Immediately updates the runtime settings so no server restart is needed.
    """
    _col().update_one(
        {"gatewayId": "razorpay"},
        {
            "$set": {
                "gatewayId": "razorpay",
                "key_id": body.key_id.strip(),
                "key_secret": body.key_secret.strip(),
            }
        },
        upsert=True,
    )
    # Propagate to runtime config immediately
    settings.razorpay_key_id = body.key_id.strip()
    settings.razorpay_key_secret = body.key_secret.strip()
    return {"message": "Razorpay configuration updated successfully"}
