"""Checkout and order application service."""
from __future__ import annotations

from contextlib import nullcontext

from fastapi import HTTPException, Request, status
from jose import jwt as jose_jwt

from app.config import settings
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.schemas.schemas import (
    OrderRequest,
    RazorpayOrderCreateRequest,
    RazorpayOrderCreateResponse,
)
from app.services.checkout_lock_service import CheckoutLockService
from app.services.customer_service import CustomerService
from app.services.order_state import is_online_payment_method
from app.services.order_writer import OrderWriterService
from app.services.payment_service import PaymentService
from app.services.pricing import calculate_order_totals
from app.services.stock_service import StockService


class CheckoutService:
    """Use-case service for payment-order creation and final order placement."""

    def __init__(self, repo: OrderCartRepository):
        self.repo = repo
        self.checkout_lock_service = CheckoutLockService(repo)
        self.customer_service = CustomerService(repo)
        self.order_writer = OrderWriterService(repo)
        self.payment_service = PaymentService(repo)
        self.stock_service = StockService(repo)

    @staticmethod
    def extract_session_id(http_request: Request) -> str:
        """Extract session id from bearer token sid claim."""
        auth = http_request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = jose_jwt.decode(
                    auth[7:], settings.secret_key, algorithms=[settings.algorithm],
                )
                sid = payload.get("sid")
                if sid:
                    return sid
            except Exception:
                pass
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    def create_razorpay_payment_order(
        self,
        request: RazorpayOrderCreateRequest,
        current_user: str,
        session_id: str,
    ) -> RazorpayOrderCreateResponse:
        """Create a Razorpay order for the active checkout."""
        if not request.cart_quote_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cart_quote_id is required for checkout")

        self.checkout_lock_service.acquire(request.cart_quote_id, session_id)

        user = self.customer_service.get_user_or_404(current_user)
        customer_business_id = self.customer_service.get_or_assign_customer_business_id(user)
        totals = calculate_order_totals(
            request,
            self.repo,
        )
        return self.payment_service.create_razorpay_payment_order(
            request,
            current_user=current_user,
            customer_business_id=customer_business_id,
            totals=totals,
        )

    def create_order(self, order_request: OrderRequest, current_user: str, session_id: str) -> dict:
        """Place an order and persist stock/payment/ledger side effects."""
        if not order_request.cart_quote_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cart_quote_id is required for checkout")

        self.checkout_lock_service.acquire(order_request.cart_quote_id, session_id)
        try:
            transaction_cm = self.repo.transaction() if hasattr(self.repo, "transaction") else nullcontext()
            with transaction_cm:
                user = self.customer_service.get_user_or_404(current_user)
                customer_business_id = self.customer_service.get_or_assign_customer_business_id(user)
                totals = calculate_order_totals(
                    order_request,
                    self.repo,
                )

                payment_status, payment_provider, payment_reference = self.payment_service.build_default_payment_state()

                if is_online_payment_method(order_request.payment_method):
                    payment_status, payment_provider, payment_reference = self.payment_service.verify_and_capture_order_payment(
                        order_request,
                        current_user=current_user,
                        expected_order_total=totals.total,
                    )

                self.stock_service.allocate_order_items(totals.items)
                addr_dict = order_request.shipping_address.model_dump()
                order_doc = self.order_writer.build_order_document(
                    order_request,
                    customer_business_id=customer_business_id,
                    totals=totals,
                    payment_status=payment_status,
                    payment_provider=payment_provider,
                    payment_reference=payment_reference,
                )
                order_response = self.order_writer.persist_order(
                    order_doc,
                    user=user,
                    current_user=current_user,
                    new_address=addr_dict,
                )
                return {"message": "Order created successfully", "order": order_response}
        finally:
            self.checkout_lock_service.release(order_request.cart_quote_id)