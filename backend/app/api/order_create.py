"""Order creation and payment API."""
from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.data.repository_providers import get_order_cart_repository
from app.schemas.schemas import (
    OrderRequest,
    RazorpayKeyConfigResponse,
    RazorpayOrderCreateRequest,
    RazorpayOrderCreateResponse,
)
from app.services.checkout_service import CheckoutService
from app.services.payment_service import PaymentService
from app.utils.rbac import require_functionality

router = APIRouter(prefix="/api/orders", tags=["Orders"])
@router.get("/payment/razorpay/config", response_model=RazorpayKeyConfigResponse)
async def get_razorpay_key_config(
    _: dict = Depends(require_functionality("customer_purchase")),
):
    """Return the Razorpay public key_id for authenticated users. Never exposes key_secret."""
    PaymentService.ensure_razorpay_configured_global()
    return RazorpayKeyConfigResponse(key_id=settings.razorpay_key_id)


@router.post("/payment/razorpay/order", response_model=RazorpayOrderCreateResponse)
async def create_razorpay_payment_order(
    request: RazorpayOrderCreateRequest,
    http_request: Request,
    ctx: dict = Depends(require_functionality("customer_purchase")),
    repo=Depends(get_order_cart_repository),
):
    """Create a Razorpay order for checkout and return key/order details for client-side payment."""
    service = CheckoutService(repo)
    return service.create_razorpay_payment_order(
        request=request,
        current_user=ctx["username"],
        session_id=service.extract_session_id(http_request),
    )


@router.post("/", response_model=dict)
async def create_order(
    order_request: OrderRequest,
    http_request: Request,
    ctx: dict = Depends(require_functionality("customer_purchase")),
    repo=Depends(get_order_cart_repository),
):
    """Create a new order"""
    service = CheckoutService(repo)
    return service.create_order(
        order_request=order_request,
        current_user=ctx["username"],
        session_id=service.extract_session_id(http_request),
    )
