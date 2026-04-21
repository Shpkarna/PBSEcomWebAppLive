"""Shared pricing business rules for cart and order flows."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status


DISCOUNT_PERCENTAGE = "Discount percentage"
DISCOUNT_AMOUNT = "Discount amount"
DISCOUNT_PER_QUANTITY = "per quantity"
DISCOUNT_TOTAL_QUANTITY = "Total quantity"
DISCOUNT_CATEGORY = "Category"


@dataclass(slots=True)
class PricingTotals:
    items: list[dict]
    subtotal: float
    total_discount: float
    total_gst: float
    total: float


def _safe_discount_value(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _compute_discount(base_amount: float, discount_kind: str | None, discount_value: float | None) -> float:
    if base_amount <= 0 or discount_kind is None or discount_value is None or discount_value < 0:
        return 0.0
    if discount_kind == DISCOUNT_PERCENTAGE:
        return max(0.0, min(base_amount, base_amount * (discount_value / 100.0)))
    if discount_kind == DISCOUNT_AMOUNT:
        return max(0.0, min(base_amount, discount_value))
    return 0.0


def _category_discount(repo, category_name: str | None, line_subtotal: float) -> float:
    if not category_name:
        return 0.0
    category_doc = repo.find_category_by_name(category_name)
    if not category_doc:
        return 0.0
    return _compute_discount(
        line_subtotal,
        category_doc.get("discount_type"),
        _safe_discount_value(category_doc.get("discount_value")),
    )


def _finalize_items(
    items: list[dict],
    subtotal_before_discount: float,
    line_discount_total: float,
    deferred_total_quantity_rules: list[dict],
) -> PricingTotals:
    intermediate_subtotal = max(0.0, subtotal_before_discount - line_discount_total)

    order_level_discount = 0.0
    for rule in deferred_total_quantity_rules:
        rule_discount = _compute_discount(
            intermediate_subtotal,
            rule.get("discount_kind"),
            rule.get("discount_value"),
        )
        if rule_discount > order_level_discount:
            order_level_discount = rule_discount

    distributed = 0.0
    for index, item in enumerate(items):
        taxable_before = max(0.0, item.get("taxable_amount", 0.0))
        if intermediate_subtotal > 0 and order_level_discount > 0:
            if index == len(items) - 1:
                share = max(0.0, order_level_discount - distributed)
            else:
                share = order_level_discount * (taxable_before / intermediate_subtotal)
                distributed += share
        else:
            share = 0.0

        taxable_after = max(0.0, taxable_before - share)
        item["discount_amount"] = max(0.0, item.get("discount_amount", 0.0)) + share
        item["taxable_amount"] = taxable_after
        item["gst_amount"] = taxable_after * item["gst_rate"]
        item["total"] = taxable_after + item["gst_amount"]

    subtotal = sum(item["taxable_amount"] for item in items)
    total_gst = sum(item["gst_amount"] for item in items)
    total_discount = min(subtotal_before_discount, line_discount_total + order_level_discount)
    total = subtotal + total_gst
    return PricingTotals(
        items=items,
        subtotal=subtotal,
        total_discount=total_discount,
        total_gst=total_gst,
        total=total,
    )


def calculate_order_totals(order_request, repo) -> PricingTotals:
    """Compute priced order lines and aggregate totals from order request items."""
    order_items: list[dict] = []
    subtotal_before_discount = 0.0
    line_discount_total = 0.0
    deferred_total_quantity_rules: list[dict] = []

    for item in order_request.items:
        product = repo.find_product_by_id(item.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {item.product_id}",
            )

        if product.get("stock_quantity", 0) < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product: {product['name']}",
            )

        gst_rate = product.get("gst_rate", 0.18)
        line_subtotal = product["sell_price"] * item.quantity
        discount_amount = 0.0

        discount_type = product.get("discount_type")
        discount_kind = product.get("discount")
        discount_value = _safe_discount_value(product.get("discount_value"))

        if discount_type == DISCOUNT_PER_QUANTITY:
            unit_discount = _compute_discount(product["sell_price"], discount_kind, discount_value)
            discount_amount = min(line_subtotal, unit_discount * item.quantity)
        elif discount_type == DISCOUNT_CATEGORY:
            discount_amount = _category_discount(repo, product.get("category"), line_subtotal)
        elif discount_type == DISCOUNT_TOTAL_QUANTITY:
            deferred_total_quantity_rules.append(
                {
                    "discount_kind": discount_kind,
                    "discount_value": discount_value,
                }
            )

        taxable_amount = max(0.0, line_subtotal - discount_amount)
        order_items.append(
            {
                "product_id": item.product_id,
                "product_name": product["name"],
                "quantity": item.quantity,
                "stock_price": product["stock_price"],
                "sell_price": product["sell_price"],
                "gst_rate": gst_rate,
                "line_subtotal": line_subtotal,
                "discount_amount": discount_amount,
                "taxable_amount": taxable_amount,
                "gst_amount": 0.0,
                "total": 0.0,
            }
        )
        subtotal_before_discount += line_subtotal
        line_discount_total += discount_amount

    return _finalize_items(
        order_items,
        subtotal_before_discount,
        line_discount_total,
        deferred_total_quantity_rules,
    )


def calculate_cart_totals(cart_items: list[dict], repo) -> PricingTotals:
    """Compute priced cart lines and aggregate totals from stored cart items."""
    priced_items: list[dict] = []
    subtotal_before_discount = 0.0
    line_discount_total = 0.0
    deferred_total_quantity_rules: list[dict] = []

    for cart_item in cart_items:
        product_name = cart_item.get("product_name", "")
        product_spec = ""
        product = None
        try:
            product = repo.find_product_by_id(cart_item["product_id"])
            if product:
                product_name = product.get("name", product_name)
                spec_parts = []
                if product.get("category"):
                    spec_parts.append(product["category"])
                if product.get("description"):
                    spec_parts.append(product["description"])
                product_spec = " | ".join(spec_parts)
        except Exception:
            product = None

        quantity = cart_item["quantity"]
        unit_price = product.get("sell_price", cart_item.get("price", 0.0)) if product else cart_item.get("price", 0.0)
        gst_rate = product.get("gst_rate", cart_item.get("gst_rate", 0.18)) if product else cart_item.get("gst_rate", 0.18)
        line_subtotal = unit_price * quantity

        discount_amount = 0.0
        if product:
            discount_type = product.get("discount_type")
            discount_kind = product.get("discount")
            discount_value = _safe_discount_value(product.get("discount_value"))
            if discount_type == DISCOUNT_PER_QUANTITY:
                unit_discount = _compute_discount(unit_price, discount_kind, discount_value)
                discount_amount = min(line_subtotal, unit_discount * quantity)
            elif discount_type == DISCOUNT_CATEGORY:
                discount_amount = _category_discount(repo, product.get("category"), line_subtotal)
            elif discount_type == DISCOUNT_TOTAL_QUANTITY:
                deferred_total_quantity_rules.append(
                    {
                        "discount_kind": discount_kind,
                        "discount_value": discount_value,
                    }
                )

        taxable_amount = max(0.0, line_subtotal - discount_amount)
        priced_items.append(
            {
                "product_id": cart_item["product_id"],
                "product_name": product_name,
                "product_spec": product_spec,
                "quantity": quantity,
                "price": unit_price,
                "line_subtotal": line_subtotal,
                "discount_amount": discount_amount,
                "taxable_amount": taxable_amount,
                "gst_amount": 0.0,
                "total": 0.0,
                "gst_rate": gst_rate,
            }
        )
        subtotal_before_discount += line_subtotal
        line_discount_total += discount_amount

    return _finalize_items(
        priced_items,
        subtotal_before_discount,
        line_discount_total,
        deferred_total_quantity_rules,
    )