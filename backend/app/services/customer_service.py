"""Customer identity coordination service for checkout flows."""
from __future__ import annotations

from fastapi import HTTPException, status

from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.utils.id_generator import next_customer_id


class CustomerService:
    """Resolves and enriches customer identity for checkout use cases."""

    def __init__(self, repo: OrderCartRepository):
        self.repo = repo

    def get_user_or_404(self, username: str) -> dict:
        user = self.repo.find_user_by_username(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def get_or_assign_customer_business_id(self, user: dict) -> str:
        customer_business_id = user.get("customer_id")
        if customer_business_id:
            return customer_business_id

        customer_business_id = next_customer_id()
        self.repo.set_customer_business_id(user["_id"], customer_business_id)
        return customer_business_id
