"""Cart application service for session-scoped cart operations."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status

from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.domain.entities import CartItemEntity
from app.schemas.schemas import CartItemRequest, CartResponse
from app.services.pricing import calculate_cart_totals


class CartService:
    """Use-case service for cart mutations and cart summary reads."""

    def __init__(self, repo: OrderCartRepository):
        self.repo = repo

    def _get_user(self, username: str) -> dict:
        user = self.repo.find_user_by_username(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def add_to_cart(self, username: str, session_id: str, item: CartItemRequest) -> dict:
        """Add an item to the current session cart with quantity guards."""
        user = self._get_user(username)
        product = self.repo.find_product_by_id(item.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or invalid product ID")
        if item.quantity > 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 5 units per product allowed")
        if product.get("stock_quantity", 0) < item.quantity:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

        user_id = str(user["_id"])
        existing = self.repo.find_cart_item(user_id, session_id, item.product_id)
        current_qty = existing["quantity"] if existing else 0
        if current_qty + item.quantity > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot exceed 5 units per product. You already have {current_qty} in cart.",
            )

        if existing:
            self.repo.update_cart_item_quantity(existing["_id"], item.quantity)
        else:
            any_cart_item = self.repo.find_any_cart_item(user_id, session_id)
            cart_quote_id = (
                any_cart_item["cart_quote_id"]
                if any_cart_item and any_cart_item.get("cart_quote_id")
                else str(uuid4())
            )
            self.repo.backfill_cart_quote_id(user_id, session_id, cart_quote_id)
            self.repo.insert_cart_item(
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "product_id": item.product_id,
                    "product_name": product["name"],
                    "quantity": item.quantity,
                    "price": product["sell_price"],
                    "gst_rate": product.get("gst_rate", 0.18),
                    "cart_quote_id": cart_quote_id,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
        return {"message": "Item added to cart"}

    def get_cart(self, username: str, session_id: str) -> CartResponse:
        """Build cart totals and item lines for the active session cart."""
        user = self._get_user(username)
        user_id = str(user["_id"])

        cart_items = self.repo.list_cart_items(user_id, session_id)
        totals = calculate_cart_totals(
            cart_items,
            self.repo,
        )

        items = []
        for item in totals.items:
            entity = CartItemEntity(
                product_id=item["product_id"],
                product_name=item.get("product_name", ""),
                product_spec=item.get("product_spec", ""),
                quantity=item["quantity"],
                price=item["price"],
                line_subtotal=item.get("line_subtotal", 0.0),
                discount_amount=item.get("discount_amount", 0.0),
                taxable_amount=item.get("taxable_amount", 0.0),
                gst_amount=item.get("gst_amount", 0.0),
                total=item.get("total", 0.0),
            )
            items.append(asdict(entity))

        return CartResponse(
            items=items,
            cart_quote_id=cart_items[0].get("cart_quote_id", "") if cart_items else "",
            subtotal=totals.subtotal,
            total_discount=totals.total_discount,
            total_gst=totals.total_gst,
            total=totals.total,
        )

    def remove_from_cart(self, username: str, session_id: str, product_id: str) -> dict:
        """Remove one product line from current session cart."""
        user = self._get_user(username)
        deleted_count = self.repo.remove_cart_item(str(user["_id"]), session_id, product_id)
        if deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")
        return {"message": "Item removed from cart"}

    def clear_cart(self, username: str, session_id: str) -> dict:
        """Clear current session cart and release associated checkout lock."""
        user = self._get_user(username)
        user_id = str(user["_id"])

        any_item = self.repo.find_any_cart_item(user_id, session_id)
        if any_item and any_item.get("cart_quote_id"):
            self.repo.release_checkout_lock(any_item["cart_quote_id"])
        self.repo.clear_session_cart(user_id, session_id)
        return {"message": "Cart cleared"}