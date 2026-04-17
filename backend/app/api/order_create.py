"""Order creation and payment API."""
from datetime import datetime, timedelta
import hashlib
import hmac

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt as jose_jwt
from pymongo.errors import DuplicateKeyError
import razorpay

from app.config import settings
from app.database import get_collection
from app.schemas.schemas import (
    OrderRequest,
    OrderResponse,
    RazorpayKeyConfigResponse,
    RazorpayOrderCreateRequest,
    RazorpayOrderCreateResponse,
)
from app.utils.id_generator import next_customer_id, next_sales_order_id
from app.utils.rbac import require_functionality

router = APIRouter(prefix="/api/orders", tags=["Orders"])

DISCOUNT_PERCENTAGE = "Discount percentage"
DISCOUNT_AMOUNT = "Discount amount"
DISCOUNT_PER_QUANTITY = "per quantity"
DISCOUNT_TOTAL_QUANTITY = "Total quantity"
DISCOUNT_CATEGORY = "Category"
ONLINE_PAYMENT_METHODS = {"card", "upi", "netbanking"}
CHECKOUT_LOCK_TTL_MINUTES = 10
_checkout_index_ensured = False


def _extract_session_id(http_request: Request) -> str:
    """Extract session_id (sid claim) from the Authorization header JWT."""
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
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session",
    )


def _acquire_checkout_lock(cart_quote_id: str, session_id: str) -> None:
    """Acquire a per-cart_quote_id checkout lock for the calling session.

    Only one session at a time may hold the checkout lock for a given
    cart_quote_id.  If a *different*, non-expired session already holds it
    the request is rejected with 409 CONFLICT.  The same session merely
    refreshes the TTL.  Different cart_quote_ids (i.e. different sessions)
    can proceed with checkout simultaneously.
    """
    global _checkout_index_ensured
    locks_col = get_collection("checkout_locks")
    now = datetime.utcnow()
    expiry = now + timedelta(minutes=CHECKOUT_LOCK_TTL_MINUTES)

    if not _checkout_index_ensured:
        locks_col.create_index("cart_quote_id", unique=True)
        _checkout_index_ensured = True

    try:
        locks_col.find_one_and_update(
            {
                "cart_quote_id": cart_quote_id,
                "$or": [
                    {"session_id": session_id},
                    {"expires_at": {"$lt": now}},
                ],
            },
            {
                "$set": {
                    "session_id": session_id,
                    "expires_at": expiry,
                    "updated_at": now,
                },
                "$setOnInsert": {"cart_quote_id": cart_quote_id, "created_at": now},
            },
            upsert=True,
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Checkout is already in progress for this cart in another session. "
                   "Please complete or cancel the existing checkout first.",
        )


def _release_checkout_lock(cart_quote_id: str) -> None:
    """Release the checkout lock after successful order completion."""
    get_collection("checkout_locks").delete_one({
        "cart_quote_id": cart_quote_id,
    })


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


def _category_discount(products_col, categories_col, product: dict, line_subtotal: float) -> float:
    category_name = product.get("category")
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


def _ensure_razorpay_configured() -> None:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Razorpay credentials are not configured",
        )


def _get_or_assign_customer_business_id(users_col, user: dict) -> str:
    customer_business_id = user.get("customer_id")
    if customer_business_id:
        return customer_business_id

    customer_business_id = next_customer_id()
    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {"customer_id": customer_business_id, "updated_at": datetime.utcnow()}},
    )
    return customer_business_id


def _calculate_order_totals(order_request, products_col, categories_col):
    order_items: list[dict] = []
    subtotal_before_discount = 0.0
    line_discount_total = 0.0
    deferred_total_quantity_rules: list[dict] = []

    for item in order_request.items:
        try:
            product_oid = ObjectId(item.product_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid product ID: {item.product_id}",
            )

        product = products_col.find_one({"_id": product_oid})
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
        item_sub = product["sell_price"] * item.quantity
        line_discount = 0.0

        discount_type = product.get("discount_type")
        product_discount_kind = product.get("discount")
        product_discount_value = _safe_discount_value(product.get("discount_value"))

        if discount_type == DISCOUNT_PER_QUANTITY:
            unit_discount = _compute_discount(
                product["sell_price"],
                product_discount_kind,
                product_discount_value,
            )
            line_discount = min(item_sub, unit_discount * item.quantity)
        elif discount_type == DISCOUNT_CATEGORY:
            line_discount = _category_discount(products_col, categories_col, product, item_sub)
        elif discount_type == DISCOUNT_TOTAL_QUANTITY:
            deferred_total_quantity_rules.append(
                {
                    "discount_kind": product_discount_kind,
                    "discount_value": product_discount_value,
                }
            )

        taxable_before_order_level = max(0.0, item_sub - line_discount)
        order_items.append(
            {
                "product_id": item.product_id,
                "product_name": product["name"],
                "quantity": item.quantity,
                "stock_price": product["stock_price"],
                "sell_price": product["sell_price"],
                "gst_rate": gst_rate,
                "line_subtotal": item_sub,
                "discount_amount": line_discount,
                "taxable_amount": taxable_before_order_level,
                "gst_amount": 0.0,
                "total": 0.0,
            }
        )
        subtotal_before_discount += item_sub
        line_discount_total += line_discount

    intermediate_subtotal = max(0.0, subtotal_before_discount - line_discount_total)

    order_level_discount = 0.0
    for rule in deferred_total_quantity_rules:
        rule_discount = _compute_discount(intermediate_subtotal, rule.get("discount_kind"), rule.get("discount_value"))
        if rule_discount > order_level_discount:
            order_level_discount = rule_discount

    distributed = 0.0
    for index, oi in enumerate(order_items):
        taxable_before = max(0.0, oi.get("taxable_amount", 0.0))
        if intermediate_subtotal > 0 and order_level_discount > 0:
            if index == len(order_items) - 1:
                share = max(0.0, order_level_discount - distributed)
            else:
                share = order_level_discount * (taxable_before / intermediate_subtotal)
                distributed += share
        else:
            share = 0.0

        taxable_after = max(0.0, taxable_before - share)
        oi["discount_amount"] = max(0.0, oi.get("discount_amount", 0.0)) + share
        oi["taxable_amount"] = taxable_after
        oi["gst_amount"] = taxable_after * oi["gst_rate"]
        oi["total"] = taxable_after + oi["gst_amount"]

    subtotal = sum(oi["taxable_amount"] for oi in order_items)
    total_gst = sum(oi["gst_amount"] for oi in order_items)
    total_discount = min(subtotal_before_discount, line_discount_total + order_level_discount)
    total = subtotal + total_gst

    return {
        "order_items": order_items,
        "subtotal": subtotal,
        "total_gst": total_gst,
        "total_discount": total_discount,
        "total": total,
    }


def _verify_razorpay_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    body = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    expected_signature = hmac.new(
        settings.razorpay_key_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, razorpay_signature)


def _verify_razorpay_payment_state(razorpay_order_id: str, razorpay_payment_id: str, expected_amount_paise: int) -> None:
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    try:
        payment = client.payment.fetch(razorpay_payment_id)
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


@router.get("/payment/razorpay/config", response_model=RazorpayKeyConfigResponse)
async def get_razorpay_key_config(
    _: dict = Depends(require_functionality("customer_purchase")),
):
    """Return the Razorpay public key_id for authenticated users. Never exposes key_secret."""
    _ensure_razorpay_configured()
    return RazorpayKeyConfigResponse(key_id=settings.razorpay_key_id)


@router.post("/payment/razorpay/order", response_model=RazorpayOrderCreateResponse)
async def create_razorpay_payment_order(
    request: RazorpayOrderCreateRequest,
    http_request: Request,
    ctx: dict = Depends(require_functionality("customer_purchase")),
):
    """Create a Razorpay order for checkout and return key/order details for client-side payment."""
    _ensure_razorpay_configured()
    current_user = ctx["username"]
    session_id = _extract_session_id(http_request)
    cart_quote_id = request.cart_quote_id
    if not cart_quote_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cart_quote_id is required for checkout")
    _acquire_checkout_lock(cart_quote_id, session_id)

    users_col = get_collection("users")
    products_col = get_collection("products")
    categories_col = get_collection("categories")
    payments_col = get_collection("payments")

    user = users_col.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    customer_business_id = _get_or_assign_customer_business_id(users_col, user)
    totals = _calculate_order_totals(request, products_col, categories_col)
    amount_paise = int(round(totals["total"] * 100))
    receipt = next_sales_order_id()

    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    try:
        rp_order = client.order.create(
            {
                "amount": amount_paise,
                "currency": settings.razorpay_currency,
                "receipt": receipt,
                "payment_capture": 1,
            }
        )
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Razorpay order creation failed: {error}")

    payments_col.insert_one(
        {
            "provider": "razorpay",
            "status": "created",
            "username": current_user,
            "customer_id": customer_business_id,
            "payment_method": request.payment_method,
            "razorpay_order_id": rp_order.get("id"),
            "amount": amount_paise,
            "currency": settings.razorpay_currency,
            "receipt": receipt,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    )

    return RazorpayOrderCreateResponse(
        key_id=settings.razorpay_key_id,
        razorpay_order_id=rp_order.get("id"),
        amount=amount_paise,
        currency=settings.razorpay_currency,
        receipt=receipt,
        total=totals["total"],
        subtotal=totals["subtotal"],
        total_gst=totals["total_gst"],
        total_discount=totals["total_discount"],
    )


@router.post("/", response_model=dict)
async def create_order(
    order_request: OrderRequest,
    http_request: Request,
    ctx: dict = Depends(require_functionality("customer_purchase")),
):
    """Create a new order"""
    current_user = ctx["username"]
    session_id = _extract_session_id(http_request)
    cart_quote_id = order_request.cart_quote_id
    if not cart_quote_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cart_quote_id is required for checkout")
    _acquire_checkout_lock(cart_quote_id, session_id)
    users_col = get_collection("users")
    products_col = get_collection("products")
    orders_col = get_collection("orders")
    ledger_col = get_collection("ledger")
    stock_ledger_col = get_collection("stock_ledger")
    categories_col = get_collection("categories")
    payments_col = get_collection("payments")

    user = users_col.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    customer_business_id = _get_or_assign_customer_business_id(users_col, user)
    totals = _calculate_order_totals(order_request, products_col, categories_col)
    order_items = totals["order_items"]
    subtotal = totals["subtotal"]
    total_gst = totals["total_gst"]
    total_discount = totals["total_discount"]
    total = totals["total"]

    payment_status = "pending"
    payment_provider = None
    payment_reference = None

    if order_request.payment_method in ONLINE_PAYMENT_METHODS:
        _ensure_razorpay_configured()
        if (
            not order_request.razorpay_order_id
            or not order_request.razorpay_payment_id
            or not order_request.razorpay_signature
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Razorpay payment proof is required for online payments",
            )

        if not _verify_razorpay_signature(
            order_request.razorpay_order_id,
            order_request.razorpay_payment_id,
            order_request.razorpay_signature,
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay signature")

        payment_record = payments_col.find_one(
            {
                "provider": "razorpay",
                "status": "created",
                "razorpay_order_id": order_request.razorpay_order_id,
                "username": current_user,
            }
        )
        if not payment_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Razorpay order not found or already consumed",
            )

        expected_amount = int(round(total * 100))
        if int(payment_record.get("amount", 0)) != expected_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Razorpay amount mismatch",
            )

        _verify_razorpay_payment_state(
            order_request.razorpay_order_id,
            order_request.razorpay_payment_id,
            expected_amount,
        )

        payments_col.update_one(
            {"_id": payment_record["_id"]},
            {
                "$set": {
                    "status": "verified",
                    "razorpay_payment_id": order_request.razorpay_payment_id,
                    "razorpay_signature": order_request.razorpay_signature,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        payment_status = "paid"
        payment_provider = "razorpay"
        payment_reference = order_request.razorpay_payment_id

    for oi in order_items:
        try:
            product_oid = ObjectId(oi["product_id"])
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid product ID in order items")

        quantity = int(oi.get("quantity", 0))
        stock_result = products_col.update_one(
            {"_id": product_oid, "stock_quantity": {"$gte": quantity}},
            {"$inc": {"stock_quantity": -quantity}, "$set": {"updated_at": datetime.utcnow()}},
        )
        if stock_result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock for product: {oi.get('product_name', oi['product_id'])}",
            )

        stock_ledger_col.insert_one(
            {
                "product_id": oi["product_id"],
                "transaction_type": "outbound",
                "quantity": quantity,
                "reference": "Order",
                "created_at": datetime.utcnow(),
            }
        )

    order_number = next_sales_order_id()
    order = {
        "customer_id": customer_business_id, "order_number": order_number,
        "cart_quote_id": cart_quote_id,
        "items": order_items, "subtotal": subtotal, "total_discount": total_discount, "total_gst": total_gst,
        "total": total, "payment_method": order_request.payment_method,
        "payment_status": payment_status,
        "payment_provider": payment_provider,
        "payment_reference": payment_reference,
        "razorpay_order_id": order_request.razorpay_order_id,
        "shipping_address": order_request.shipping_address.model_dump(),
        "shipment_date": order_request.shipment_date,
        "status": "confirmed" if order_request.payment_method == "cod" or order_request.payment_method in ONLINE_PAYMENT_METHODS else "pending",
        "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
    }
    result = orders_col.insert_one(order)
    order["_id"] = result.inserted_id

    # Sync shipping address to user profile if different
    addr_dict = order_request.shipping_address.model_dump()
    current_addr = user.get("address_data") or {}
    if addr_dict != current_addr:
        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"address_data": addr_dict, "updated_at": datetime.utcnow()}},
        )

    ledger_col.insert_one({
        "transaction_type": "credit", "category": "sales",
        "amount": total, "reference_id": order_number,
        "notes": f"Sale to {current_user}", "created_at": datetime.utcnow(),
    })

    _release_checkout_lock(cart_quote_id)
    return {"message": "Order created successfully", "order": OrderResponse(**order)}
