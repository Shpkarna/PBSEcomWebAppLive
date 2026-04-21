"""Checkout lock lifecycle coordination service."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.domain.contracts.order_cart_repository import OrderCartRepository


DEFAULT_CHECKOUT_LOCK_TTL_MINUTES = 10


class CheckoutLockService:
    """Manages checkout lock acquisition/release semantics for cart quote ids."""

    def __init__(self, repo: OrderCartRepository, ttl_minutes: int = DEFAULT_CHECKOUT_LOCK_TTL_MINUTES):
        self.repo = repo
        self.ttl_minutes = ttl_minutes

    def acquire(self, cart_quote_id: str, session_id: str) -> None:
        try:
            self.repo.acquire_checkout_lock(cart_quote_id, session_id, self.ttl_minutes)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Checkout is already in progress for this cart in another session. "
                    "Please complete or cancel the existing checkout first."
                ),
            )

    def release(self, cart_quote_id: str) -> None:
        self.repo.release_checkout_lock(cart_quote_id)
