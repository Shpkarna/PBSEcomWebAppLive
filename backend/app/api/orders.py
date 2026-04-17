"""Orders list, detail, and status API routes."""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from app.database import get_collection
from app.schemas.schemas import OrderResponse, ReturnRequest, ExchangeRequest
from app.utils.security import decode_token, get_token_from_credentials, security
from app.utils.rbac import require_role, require_functionality
from app.utils.id_generator import next_sales_order_id, next_customer_id
from bson import ObjectId
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = get_token_from_credentials(credentials)
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload.get("sub")


def _normalize_order(o: dict) -> dict:
    """Normalize legacy order data for consistent serialization."""
    addr = o.get("shipping_address")
    if isinstance(addr, str):
        o["shipping_address"] = {"street1": addr, "street2": "", "landmark": "",
                                  "district": "", "area": "", "state": "",
                                  "country": "", "pincode": "", "phone": ""}
    return o


def _customer_keys(user: dict) -> list[str]:
    """Return both legacy and new customer identifiers for compatibility."""
    keys = {str(user["_id"])}
    if user.get("customer_id"):
        keys.add(user["customer_id"])
    return list(keys)


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
    current_user: str = Depends(get_current_user),
):
    """List orders for current user"""
    users_col = get_collection("users")
    orders_col = get_collection("orders")
    user = users_col.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    orders = list(
        orders_col.find({"customer_id": {"$in": _customer_keys(user)}})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    return [OrderResponse(**_normalize_order(o)) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, current_user: str = Depends(get_current_user)):
    """Get order details"""
    users_col = get_collection("users")
    orders_col = get_collection("orders")
    try:
        order_oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID")
    user = users_col.find_one({"username": current_user})
    order = orders_col.find_one({"_id": order_oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.get("customer_id") not in _customer_keys(user) and user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this order")
    return OrderResponse(**_normalize_order(order))


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: str, new_status: str,
    _: dict = Depends(require_role(["admin"])),
):
    """Update order status (Admin only)"""
    orders_col = get_collection("orders")
    try:
        order_oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID")

    valid = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "return_requested", "returned"]
    if new_status not in valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid status. Must be one of: {', '.join(valid)}")

    result = orders_col.update_one({"_id": order_oid}, {"$set": {"status": new_status, "updated_at": datetime.utcnow()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return {"message": f"Order status updated to {new_status}"}


@router.post("/{order_id}/return")
async def return_order(
    order_id: str,
    body: ReturnRequest,
    ctx: dict = Depends(require_functionality("customer_purchase")),
):
    """Request return for a delivered order."""
    current_user = ctx["username"]
    users_col = get_collection("users")
    orders_col = get_collection("orders")
    products_col = get_collection("products")
    stock_ledger_col = get_collection("stock_ledger")

    user = users_col.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        order_oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID")

    order = orders_col.find_one({"_id": order_oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.get("customer_id") not in _customer_keys(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    if order["status"] != "delivered":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Only delivered orders can be returned")

    # Return stock for each item
    for item in order.get("items", []):
        try:
            prod_oid = ObjectId(item["product_id"])
            products_col.update_one(
                {"_id": prod_oid},
                {"$inc": {"stock_quantity": item["quantity"]},
                 "$set": {"updated_at": datetime.utcnow()}},
            )
            stock_ledger_col.insert_one({
                "product_id": item["product_id"],
                "transaction_type": "inbound",
                "quantity": item["quantity"],
                "reference": f"Return from order {order.get('order_number', order_id)}",
                "notes": body.reason,
                "created_at": datetime.utcnow(),
            })
        except Exception:
            pass

    orders_col.update_one(
        {"_id": order_oid},
        {"$set": {"status": "returned", "return_reason": body.reason, "updated_at": datetime.utcnow()}},
    )
    updated = orders_col.find_one({"_id": order_oid})
    return {"message": "Order returned successfully", "order": OrderResponse(**_normalize_order(updated))}


@router.post("/{order_id}/exchange")
async def exchange_order(
    order_id: str,
    body: ExchangeRequest,
    ctx: dict = Depends(require_functionality("customer_purchase")),
):
    """Exchange a delivered order for a new product with price adjustment.

    If new product price > old order total: user gets discount to match old price.
    If new product price <= old order total: new product issued at full discount (free).
    """
    current_user = ctx["username"]
    users_col = get_collection("users")
    orders_col = get_collection("orders")
    products_col = get_collection("products")
    stock_ledger_col = get_collection("stock_ledger")
    ledger_col = get_collection("ledger")

    user = users_col.find_one({"username": current_user})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        order_oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid order ID")

    order = orders_col.find_one({"_id": order_oid})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.get("customer_id") not in _customer_keys(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    if order["status"] not in ("delivered", "returned"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Only delivered or returned orders can be exchanged")

    # Validate new product
    try:
        new_prod_oid = ObjectId(body.new_product_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid new product ID")

    new_product = products_col.find_one({"_id": new_prod_oid})
    if not new_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="New product not found")
    if new_product.get("stock_quantity", 0) < body.quantity:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Insufficient stock for the new product")

    # Return stock for old order items if not already returned
    if order["status"] == "delivered":
        for item in order.get("items", []):
            try:
                prod_oid = ObjectId(item["product_id"])
                products_col.update_one(
                    {"_id": prod_oid},
                    {"$inc": {"stock_quantity": item["quantity"]},
                     "$set": {"updated_at": datetime.utcnow()}},
                )
                stock_ledger_col.insert_one({
                    "product_id": item["product_id"],
                    "transaction_type": "inbound",
                    "quantity": item["quantity"],
                    "reference": f"Exchange return from order {order.get('order_number', order_id)}",
                    "notes": body.reason,
                    "created_at": datetime.utcnow(),
                })
            except Exception:
                pass

    # Calculate price adjustment
    old_total = order.get("total", 0)
    gst_rate = new_product.get("gst_rate", 0.18)
    new_item_subtotal = new_product["sell_price"] * body.quantity
    new_item_gst = new_item_subtotal * gst_rate
    new_item_total = new_item_subtotal + new_item_gst

    # Price adjustment: if new > old, user pays difference (gets discount to match old price)
    # if new <= old, user gets it free (full discount)
    if new_item_total > old_total:
        discount = new_item_total - old_total
        adjusted_total = old_total  # user pays only old price
    else:
        discount = new_item_total
        adjusted_total = 0  # fully discounted

    # Deduct stock for new product
    products_col.update_one(
        {"_id": new_prod_oid},
        {"$inc": {"stock_quantity": -body.quantity},
         "$set": {"updated_at": datetime.utcnow()}},
    )
    stock_ledger_col.insert_one({
        "product_id": body.new_product_id,
        "transaction_type": "outbound",
        "quantity": body.quantity,
        "reference": f"Exchange order",
        "notes": f"Exchange for order {order.get('order_number', order_id)}",
        "created_at": datetime.utcnow(),
    })

    # Create new exchange order
    customer_business_id = user.get("customer_id")
    if not customer_business_id:
        customer_business_id = next_customer_id()
        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"customer_id": customer_business_id, "updated_at": datetime.utcnow()}},
        )

    exchange_order_number = next_sales_order_id()
    new_order_items = [{
        "product_id": body.new_product_id,
        "product_name": new_product["name"],
        "quantity": body.quantity,
        "stock_price": new_product["stock_price"],
        "sell_price": new_product["sell_price"],
        "gst_rate": gst_rate,
        "gst_amount": new_item_gst,
        "total": new_item_total,
    }]

    exchange_order_doc = {
        "customer_id": customer_business_id,
        "order_number": exchange_order_number,
        "items": new_order_items,
        "subtotal": new_item_subtotal,
        "total_gst": new_item_gst,
        "total": adjusted_total,
        "discount": discount,
        "payment_method": order.get("payment_method", "cash"),
        "shipping_address": order.get("shipping_address", ""),
        "shipment_date": None,
        "status": "confirmed",
        "exchange_for_order": str(order["_id"]),
        "return_reason": body.reason,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = orders_col.insert_one(exchange_order_doc)
    exchange_order_doc["_id"] = result.inserted_id

    # Mark original order as returned with exchange reference
    orders_col.update_one(
        {"_id": order_oid},
        {"$set": {
            "status": "returned",
            "return_reason": body.reason,
            "exchange_order_id": str(result.inserted_id),
            "updated_at": datetime.utcnow(),
        }},
    )

    # Ledger entry for exchange
    if adjusted_total > 0:
        ledger_col.insert_one({
            "transaction_type": "credit", "category": "exchange_sales",
            "amount": adjusted_total, "reference_id": exchange_order_number,
            "notes": f"Exchange sale to {current_user} (discount: {discount:.2f})",
            "created_at": datetime.utcnow(),
        })

    return {
        "message": "Exchange order created successfully",
        "exchange_order": OrderResponse(**_normalize_order(exchange_order_doc)),
        "discount_applied": discount,
        "original_total": old_total,
        "new_product_total": new_item_total,
        "adjusted_total": adjusted_total,
    }
