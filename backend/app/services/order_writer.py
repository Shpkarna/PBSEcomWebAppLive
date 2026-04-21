"""Order assembly and persistence service."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.domain.entities import OrderEntity, OrderItemEntity, ShippingAddress
from app.models.enums import PaymentMethod
from app.schemas.schemas import OrderRequest, OrderResponse
from app.services.order_state import resolve_initial_order_status
from app.utils.id_generator import next_sales_order_id


class OrderWriterService:
    """Builds order domain objects and persists final order side effects."""

    def __init__(self, repo: OrderCartRepository):
        self.repo = repo

    def build_order_document(
        self,
        order_request: OrderRequest,
        *,
        customer_business_id: str,
        totals,
        payment_status: str,
        payment_provider: str | None,
        payment_reference: str | None,
    ) -> dict:
        order_items = [
            OrderItemEntity(
                product_id=item["product_id"],
                product_name=item.get("product_name", ""),
                quantity=int(item.get("quantity", 0)),
                sell_price=float(item.get("sell_price", 0.0)),
                line_subtotal=float(item.get("line_subtotal", 0.0)),
                discount_amount=float(item.get("discount_amount", 0.0)),
                taxable_amount=float(item.get("taxable_amount", 0.0)),
                gst_amount=float(item.get("gst_amount", 0.0)),
                total=float(item.get("total", 0.0)),
            )
            for item in totals.items
        ]

        now = datetime.utcnow()
        shipping = ShippingAddress(**order_request.shipping_address.model_dump())
        order_entity = OrderEntity(
            customer_id=customer_business_id,
            order_number=next_sales_order_id(),
            cart_quote_id=order_request.cart_quote_id,
            items=order_items,
            subtotal=totals.subtotal,
            total_discount=totals.total_discount,
            total_gst=totals.total_gst,
            total=totals.total,
            payment_method=PaymentMethod(order_request.payment_method),
            shipping_address=shipping,
            shipment_date=order_request.shipment_date,
            status=resolve_initial_order_status(order_request.payment_method, payment_status),
            created_at=now,
            updated_at=now,
        )

        return {
            "customer_id": order_entity.customer_id,
            "order_number": order_entity.order_number,
            "cart_quote_id": order_entity.cart_quote_id,
            "items": [asdict(item) for item in order_entity.items],
            "subtotal": order_entity.subtotal,
            "total_discount": order_entity.total_discount,
            "total_gst": order_entity.total_gst,
            "total": order_entity.total,
            "payment_method": order_entity.payment_method.value,
            "payment_status": payment_status,
            "payment_provider": payment_provider,
            "payment_reference": payment_reference,
            "razorpay_order_id": order_request.razorpay_order_id,
            "shipping_address": asdict(order_entity.shipping_address) if order_entity.shipping_address else None,
            "shipment_date": order_entity.shipment_date,
            "status": order_entity.status.value,
            "created_at": order_entity.created_at,
            "updated_at": order_entity.updated_at,
        }

    def persist_order(self, order_doc: dict, *, user: dict, current_user: str, new_address: dict) -> OrderResponse:
        order_doc["_id"] = self.repo.insert_order(order_doc)

        self.repo.update_user_address_data_if_changed(user["_id"], user.get("address_data") or {}, new_address)

        self.repo.insert_sales_ledger_row(
            {
                "transaction_type": "credit",
                "category": "sales",
                "amount": order_doc["total"],
                "reference_id": order_doc["order_number"],
                "notes": f"Sale to {current_user}",
                "created_at": datetime.utcnow(),
            }
        )

        return OrderResponse(**order_doc)
