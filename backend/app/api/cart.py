"""Cart API routes"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from app.database import get_collection
from app.schemas.schemas import CartItemRequest, CartResponse
from app.utils.security import decode_token, get_token_from_credentials, security
from bson import ObjectId
from datetime import datetime
from uuid import uuid4

router = APIRouter(prefix="/api/cart", tags=["Cart"])

DISCOUNT_PERCENTAGE = "Discount percentage"
DISCOUNT_AMOUNT = "Discount amount"
DISCOUNT_PER_QUANTITY = "per quantity"
DISCOUNT_TOTAL_QUANTITY = "Total quantity"
DISCOUNT_CATEGORY = "Category"


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


def _category_discount(categories_col, category_name: str | None, line_subtotal: float) -> float:
    if not category_name:
        return 0.0
    category_doc = categories_col.find_one({"name": category_name})
    if not category_doc:
        return 0.0
    return _compute_discount(
        line_subtotal,
        category_doc.get("discount_type"),
        _safe_discount_value(category_doc.get("discount_value")),
    )


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    username = payload.get("sub")
    session_id = payload.get("sid")
    if not username or not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
    return {"username": username, "session_id": session_id}


@router.post("/add")
async def add_to_cart(item: CartItemRequest, current_user: dict = Depends(get_current_user)):
    """Add item to cart"""
    username = current_user["username"]
    session_id = current_user["session_id"]
    users_col = get_collection("users")
    products_col = get_collection("products")
    cart_col = get_collection("cart")

    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        product_oid = ObjectId(item.product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID")

    product = products_col.find_one({"_id": product_oid})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if item.quantity > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 5 units per product allowed")
    if product.get("stock_quantity", 0) < item.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient stock")

    # Cart is scoped by (user_id, session_id)
    user_id = str(user["_id"])
    existing = cart_col.find_one({"user_id": user_id, "session_id": session_id, "product_id": item.product_id})
    current_qty = existing["quantity"] if existing else 0
    if current_qty + item.quantity > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot exceed 5 units per product. You already have {current_qty} in cart.")

    if existing:
        cart_col.update_one(
            {"_id": existing["_id"]},
            {"$set": {"quantity": existing["quantity"] + item.quantity, "updated_at": datetime.utcnow()}},
        )
    else:
        # Resolve or create a cart_quote_id for this session's cart
        any_cart_item = cart_col.find_one({"user_id": user_id, "session_id": session_id})
        cart_quote_id = any_cart_item["cart_quote_id"] if any_cart_item and any_cart_item.get("cart_quote_id") else str(uuid4())
        # Back-fill existing items in this session that lack the quote id
        cart_col.update_many(
            {"user_id": user_id, "session_id": session_id, "cart_quote_id": {"$exists": False}},
            {"$set": {"cart_quote_id": cart_quote_id}},
        )
        cart_col.insert_one({
            "user_id": user_id, "session_id": session_id, "product_id": item.product_id,
            "product_name": product["name"], "quantity": item.quantity,
            "price": product["sell_price"], "gst_rate": product.get("gst_rate", 0.18),
            "cart_quote_id": cart_quote_id,
            "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
        })
    return {"message": "Item added to cart"}


@router.get("/", response_model=CartResponse)
async def get_cart(current_user: dict = Depends(get_current_user)):
    """Get user's cart for the current session"""
    username = current_user["username"]
    session_id = current_user["session_id"]
    users_col = get_collection("users")
    cart_col = get_collection("cart")
    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_id = str(user["_id"])
    cart_items = list(cart_col.find({"user_id": user_id, "session_id": session_id}))
    products_col = get_collection("products")
    categories_col = get_collection("categories")

    items = []
    subtotal_before_discount, line_discount_total = 0.0, 0.0
    deferred_total_quantity_rules: list[dict] = []

    for ci in cart_items:
        # Look up product details from products collection so cart summary stays aligned with checkout pricing.
        product_name = ci.get("product_name", "")
        product_spec = ""
        product = None
        try:
            product = products_col.find_one({"_id": ObjectId(ci["product_id"])})
            if product:
                product_name = product.get("name", product_name)
                spec_parts = []
                if product.get("category"):
                    spec_parts.append(product["category"])
                if product.get("description"):
                    spec_parts.append(product["description"])
                product_spec = " | ".join(spec_parts)
        except Exception:
            pass

        quantity = ci["quantity"]
        unit_price = product.get("sell_price", ci.get("price", 0.0)) if product else ci.get("price", 0.0)
        gst_rate = product.get("gst_rate", ci.get("gst_rate", 0.18)) if product else ci.get("gst_rate", 0.18)
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
                discount_amount = _category_discount(categories_col, product.get("category"), line_subtotal)
            elif discount_type == DISCOUNT_TOTAL_QUANTITY:
                deferred_total_quantity_rules.append({
                    "discount_kind": discount_kind,
                    "discount_value": discount_value,
                })

        taxable_amount = max(0.0, line_subtotal - discount_amount)
        items.append({
            "product_id": ci["product_id"],
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
        })
        subtotal_before_discount += line_subtotal
        line_discount_total += discount_amount

    intermediate_subtotal = max(0.0, subtotal_before_discount - line_discount_total)

    # Apply at most one order-level rule for Total quantity discounts.
    order_level_discount = 0.0
    for rule in deferred_total_quantity_rules:
        rule_discount = _compute_discount(intermediate_subtotal, rule.get("discount_kind"), rule.get("discount_value"))
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
        gst_amount = taxable_after * item["gst_rate"]
        item["discount_amount"] = max(0.0, item.get("discount_amount", 0.0)) + share
        item["taxable_amount"] = taxable_after
        item["gst_amount"] = gst_amount
        item["total"] = taxable_after + gst_amount
        item.pop("gst_rate", None)

    subtotal = sum(i["taxable_amount"] for i in items)
    total_gst = sum(i["gst_amount"] for i in items)
    total_discount = min(subtotal_before_discount, line_discount_total + order_level_discount)

    return CartResponse(
        items=items,
        cart_quote_id=cart_items[0].get("cart_quote_id", "") if cart_items else "",
        subtotal=subtotal,
        total_discount=total_discount,
        total_gst=total_gst,
        total=subtotal + total_gst,
    )


@router.delete("/item/{product_id}")
async def remove_from_cart(product_id: str, current_user: dict = Depends(get_current_user)):
    """Remove item from cart"""
    username = current_user["username"]
    session_id = current_user["session_id"]
    users_col = get_collection("users")
    cart_col = get_collection("cart")
    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    result = cart_col.delete_one({"user_id": str(user["_id"]), "session_id": session_id, "product_id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in cart")
    return {"message": "Item removed from cart"}


@router.delete("/")
async def clear_cart(current_user: dict = Depends(get_current_user)):
    """Clear user's cart for the current session"""
    username = current_user["username"]
    session_id = current_user["session_id"]
    users_col = get_collection("users")
    cart_col = get_collection("cart")
    checkout_locks_col = get_collection("checkout_locks")
    user = users_col.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_id = str(user["_id"])
    # Find the cart_quote_id to release any associated checkout lock
    any_item = cart_col.find_one({"user_id": user_id, "session_id": session_id})
    if any_item and any_item.get("cart_quote_id"):
        checkout_locks_col.delete_one({"cart_quote_id": any_item["cart_quote_id"]})
    cart_col.delete_many({"user_id": user_id, "session_id": session_id})
    return {"message": "Cart cleared"}
