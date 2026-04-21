"""Stock allocation and ledger side effects for order placement."""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status

from app.domain.contracts.order_cart_repository import OrderCartRepository


class StockService:
    """Coordinates stock mutations required to fulfill an order."""

    def __init__(self, repo: OrderCartRepository):
        self.repo = repo

    def allocate_order_items(self, items: list[dict]) -> None:
        """Reserve stock for each order item and record outbound ledger entries."""
        for item in items:
            quantity = int(item.get("quantity", 0))
            if not self.repo.decrement_product_stock_if_available(item["product_id"], quantity):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient stock for product: {item.get('product_name', item['product_id'])}",
                )

            self.repo.insert_stock_ledger_row(
                {
                    "product_id": item["product_id"],
                    "transaction_type": "outbound",
                    "quantity": quantity,
                    "reference": "Order",
                    "created_at": datetime.utcnow(),
                }
            )
