"""Domain rules for order and payment state transitions."""
from __future__ import annotations

from typing import Optional, Tuple

from app.models.enums import OrderStatus, PaymentMethod


ONLINE_PAYMENT_METHODS = {
    PaymentMethod.CARD.value,
    PaymentMethod.UPI.value,
    PaymentMethod.NETBANKING.value,
}


def is_online_payment_method(payment_method: str) -> bool:
    """Return True when payment method requires online gateway verification."""
    return payment_method in ONLINE_PAYMENT_METHODS


def build_pending_payment_state() -> Tuple[str, Optional[str], Optional[str]]:
    """Default payment metadata before an online payment is verified."""
    return "pending", None, None


def build_paid_razorpay_state(payment_reference: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Payment metadata after successful Razorpay verification."""
    return "paid", "razorpay", payment_reference


def resolve_initial_order_status(payment_method: str, payment_status: str) -> OrderStatus:
    """Resolve initial order status from payment method and current payment state."""
    if payment_method == PaymentMethod.COD.value:
        return OrderStatus.CONFIRMED

    if is_online_payment_method(payment_method) and payment_status == "paid":
        return OrderStatus.CONFIRMED

    return OrderStatus.PENDING
