"""Payment orchestration for checkout flows."""
from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
from typing import Callable, Optional, Tuple

from fastapi import HTTPException, status
import razorpay

from app.config import settings
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.schemas.schemas import OrderRequest, RazorpayOrderCreateRequest, RazorpayOrderCreateResponse
from app.services.order_state import build_paid_razorpay_state, build_pending_payment_state
from app.utils.id_generator import next_sales_order_id


class PaymentService:
    """Coordinates payment gateway requests and payment-record state transitions."""

    def __init__(
        self,
        repo: OrderCartRepository,
        *,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        currency: Optional[str] = None,
        client_factory: Optional[Callable[..., object]] = None,
    ):
        self.repo = repo
        self.key_id = key_id if key_id is not None else settings.razorpay_key_id
        self.key_secret = key_secret if key_secret is not None else settings.razorpay_key_secret
        self.currency = currency if currency is not None else settings.razorpay_currency
        self.client_factory = client_factory or (lambda **kwargs: razorpay.Client(**kwargs))

    @staticmethod
    def ensure_razorpay_configured_global() -> None:
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Razorpay credentials are not configured",
            )

    def ensure_razorpay_configured(self) -> None:
        if not self.key_id or not self.key_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Razorpay credentials are not configured",
            )

    def _client(self):
        return self.client_factory(auth=(self.key_id, self.key_secret))

    def _verify_razorpay_signature(self, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        body = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
        expected_signature = hmac.new(
            self.key_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, razorpay_signature)

    def _verify_razorpay_payment_state(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        expected_amount_paise: int,
    ) -> None:
        try:
            payment = self._client().payment.fetch(razorpay_payment_id)
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to verify Razorpay payment: {error}",
            )

        if payment.get("order_id") != razorpay_order_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay payment order mismatch")

        payment_status = str(payment.get("status", "")).lower()
        if payment_status not in {"authorized", "captured"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay payment is not successful")

        paid_amount = int(payment.get("amount", 0))
        if paid_amount != expected_amount_paise:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay paid amount mismatch")

    def create_razorpay_payment_order(
        self,
        request: RazorpayOrderCreateRequest,
        *,
        current_user: str,
        customer_business_id: str,
        totals,
    ) -> RazorpayOrderCreateResponse:
        self.ensure_razorpay_configured()

        amount_paise = int(round(totals.total * 100))
        receipt = next_sales_order_id()

        try:
            gateway_order = self._client().order.create(
                {
                    "amount": amount_paise,
                    "currency": self.currency,
                    "receipt": receipt,
                    "payment_capture": 1,
                }
            )
        except Exception as error:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Razorpay order creation failed: {error}")

        self.repo.insert_payment_record(
            {
                "provider": "razorpay",
                "status": "created",
                "username": current_user,
                "customer_id": customer_business_id,
                "payment_method": request.payment_method,
                "razorpay_order_id": gateway_order.get("id"),
                "amount": amount_paise,
                "currency": self.currency,
                "receipt": receipt,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

        return RazorpayOrderCreateResponse(
            key_id=self.key_id,
            razorpay_order_id=gateway_order.get("id"),
            amount=amount_paise,
            currency=self.currency,
            receipt=receipt,
            total=totals.total,
            subtotal=totals.subtotal,
            total_gst=totals.total_gst,
            total_discount=totals.total_discount,
        )

    def verify_and_capture_order_payment(
        self,
        order_request: OrderRequest,
        *,
        current_user: str,
        expected_order_total: float,
    ) -> Tuple[str, Optional[str], Optional[str]]:
        self.ensure_razorpay_configured()

        if (
            not order_request.razorpay_order_id
            or not order_request.razorpay_payment_id
            or not order_request.razorpay_signature
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Razorpay payment proof is required for online payments",
            )

        if not self._verify_razorpay_signature(
            order_request.razorpay_order_id,
            order_request.razorpay_payment_id,
            order_request.razorpay_signature,
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay signature")

        payment_record = self.repo.find_pending_razorpay_payment(order_request.razorpay_order_id, current_user)
        if not payment_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Razorpay order not found or already consumed",
            )

        expected_amount = int(round(expected_order_total * 100))
        if int(payment_record.get("amount", 0)) != expected_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Razorpay amount mismatch",
            )

        self._verify_razorpay_payment_state(
            order_request.razorpay_order_id,
            order_request.razorpay_payment_id,
            expected_amount,
        )

        self.repo.mark_payment_verified(
            payment_record["_id"],
            order_request.razorpay_payment_id,
            order_request.razorpay_signature,
        )
        return build_paid_razorpay_state(order_request.razorpay_payment_id)

    @staticmethod
    def build_default_payment_state() -> Tuple[str, Optional[str], Optional[str]]:
        return build_pending_payment_state()
