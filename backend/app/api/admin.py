"""Admin API: sample data load/discard and admin-only CRUD."""
import json
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional

from app.data.repository_providers import get_order_cart_repository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.utils.rbac import require_role
from app.utils.security import hash_password
from app.config import settings
from app.data.sample_data import (
    SAMPLE_CATEGORIES, SAMPLE_VENDORS, SAMPLE_USERS,
    SAMPLE_PRODUCTS, SAMPLE_ORDERS,
    SAMPLE_CART_ITEMS, SAMPLE_SAVED_PRODUCTS,
    SAMPLE_STOCK_LEDGER, SAMPLE_LEDGER,
    SAMPLE_CONTACT_INQUIRIES, SAMPLE_USER_ROLE_MAPPINGS,
    SAMPLE_ROLE_FUNCTIONALITY_MAPPINGS, get_now,
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

_INDEX_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "sample_index.json")
_INDEX_FILE = os.path.normpath(_INDEX_FILE)


def _load_index() -> dict:
    if os.path.exists(_INDEX_FILE):
        with open(_INDEX_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_index(data: dict) -> None:
    with open(_INDEX_FILE, "w") as f:
        json.dump(data, f, indent=2)


@router.post("/load-sample-data")
async def load_sample_data(
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """Load sample data into all collections. Admin only. Dev/test use."""
    if settings.package_option == "prod":
        raise HTTPException(status_code=403, detail="Sample data tools are disabled in production")
    now = get_now()
    index: dict = {}

    cat_ids = []
    for cat in SAMPLE_CATEGORIES:
        existing = repo.find_one("categories", {"name": cat["name"]})
        if not existing:
            stored = repo.insert_one("categories", {**cat, "created_at": now})
            cat_ids.append(stored.get("id", ""))
    index["categories"] = cat_ids

    vend_ids = []
    for v in SAMPLE_VENDORS:
        existing = repo.find_one("vendors", {"email": v["email"]})
        if not existing:
            stored = repo.insert_one("vendors", {**v, "created_at": now})
            vend_ids.append(stored.get("id", ""))
    index["vendors"] = vend_ids

    user_ids = []
    for u in SAMPLE_USERS:
        existing = repo.find_one("users", {"username": u["username"]})
        if not existing:
            rec = {**u, "password_hash": hash_password("Sample@123"),
                   "created_at": now, "updated_at": now}
            stored = repo.insert_one("users", rec)
            user_ids.append(stored.get("id", ""))
    index["users"] = user_ids

    prod_ids = []
    for p in SAMPLE_PRODUCTS:
        existing = repo.find_one("products", {"sku": p["sku"]})
        if not existing:
            stored = repo.insert_one("products", {**p, "created_at": now, "updated_at": now})
            prod_ids.append(stored.get("id", ""))
    index["products"] = prod_ids

    sample_customer = repo.find_one("users", {"username": "customer1"})
    order_ids = []
    if sample_customer:
        for o in SAMPLE_ORDERS:
            # Enrich order items with product_id from DB
            enriched_items = []
            for oi in o.get("items", []):
                item_copy = {**oi}
                if "product_id" not in item_copy:
                    prod = repo.find_one("products", {"name": oi.get("product_name", "")})
                    if prod:
                        item_copy["product_id"] = prod.get("id", "")
                    else:
                        item_copy["product_id"] = "unknown"
                enriched_items.append(item_copy)
            customer_id = sample_customer.get("id", "")
            order_doc = {**o, "items": enriched_items,
                         "customer_id": customer_id,
                         "created_at": now, "updated_at": now}
            stored = repo.insert_one("orders", order_doc)
            order_ids.append(stored.get("id", ""))
    index["orders"] = order_ids

    # Cart items (linked to sample customer)
    cart_ids = []
    if sample_customer:
        for ci in SAMPLE_CART_ITEMS:
            prod = repo.find_one("products", {"sku": ci["product_sku"]})
            if prod:
                rec = {"user_id": sample_customer.get("id", ""),
                       "product_id": prod.get("id", ""),
                       "product_name": prod["name"],
                       "quantity": ci["quantity"],
                       "price": prod["sell_price"],
                       "gst_rate": prod.get("gst_rate", 0.18),
                       "created_at": now, "updated_at": now}
                stored = repo.insert_one("cart", rec)
                cart_ids.append(stored.get("id", ""))
    index["cart"] = cart_ids

    # Saved products (linked to sample customer)
    saved_ids = []
    if sample_customer:
        for sp in SAMPLE_SAVED_PRODUCTS:
            prod = repo.find_one("products", {"sku": sp["product_sku"]})
            if prod:
                rec = {"user_id": sample_customer.get("id", ""),
                       "product_id": prod.get("id", ""), "created_at": now}
                stored = repo.insert_one("saved_products", rec)
                saved_ids.append(stored.get("id", ""))
    index["saved_products"] = saved_ids

    # Stock ledger
    stock_ids = []
    for sl in SAMPLE_STOCK_LEDGER:
        prod = repo.find_one("products", {"sku": sl["product_sku"]})
        if prod:
            rec = {"product_id": prod.get("id", ""),
                   "transaction_type": sl["transaction_type"],
                   "quantity": sl["quantity"],
                   "reference": sl["reference"],
                   "notes": sl.get("notes", ""),
                   "created_at": now}
            stored = repo.insert_one("stock_ledger", rec)
            stock_ids.append(stored.get("id", ""))
    index["stock_ledger"] = stock_ids

    # Ledger
    ledger_ids = []
    for le in SAMPLE_LEDGER:
        rec = {**le, "created_at": now}
        stored = repo.insert_one("ledger", rec)
        ledger_ids.append(stored.get("id", ""))
    index["ledger"] = ledger_ids

    # Contact inquiries
    contact_ids = []
    for ci in SAMPLE_CONTACT_INQUIRIES:
        rec = {**ci, "created_at": now, "status": "new"}
        stored = repo.insert_one("contact_inquiries", rec)
        contact_ids.append(stored.get("id", ""))
    index["contact_inquiries"] = contact_ids

    # User-role mappings
    urm_ids = []
    for urm in SAMPLE_USER_ROLE_MAPPINGS:
        u = repo.find_one("users", {"username": urm["username"]})
        if u:
            existing = repo.find_one("user_role_mappings", {"username": urm["username"]})
            if not existing:
                rec = {"user_id": u.get("id", ""), "username": urm["username"],
                       "role": urm["role"], "created_at": now}
                stored = repo.insert_one("user_role_mappings", rec)
                urm_ids.append(stored.get("id", ""))
    index["user_role_mappings"] = urm_ids

    # Role-functionality mappings
    rfm_ids = []
    for rfm in SAMPLE_ROLE_FUNCTIONALITY_MAPPINGS:
        existing = repo.find_one("role_functionality_mappings", {"role": rfm["role"],
                                     "functionality_code": rfm["functionality_code"]})
        if not existing:
            rec = {**rfm, "created_at": now}
            stored = repo.insert_one("role_functionality_mappings", rec)
            rfm_ids.append(stored.get("id", ""))
    index["role_functionality_mappings"] = rfm_ids

    _save_index(index)
    total = sum(len(v) for v in index.values())
    return {"message": f"Sample data loaded: {total} records", "summary": index}


@router.post("/discard-sample-data")
async def discard_sample_data(
    _: dict = Depends(require_role(["admin"])),
    repo: OrderCartRepository = Depends(get_order_cart_repository),
):
    """
    Comprehensive data reset: clear all transaction/master data and remove all non-admin users.
    Preserves only the admin user. Admin only. Dev/test use.
    """
    if settings.package_option == "prod":
        raise HTTPException(status_code=403, detail="Sample data tools are disabled in production")
    
    deleted: dict = {}
    
    # Transaction collections - clear completely
    transaction_collections = [
        "orders",
        "order_items",
        "payments",
        "invoices",
        "carts",
        "cart",
        "contact_inquiries",
        "saved_products",
    ]
    for coll_name in transaction_collections:
        count = repo.delete_many(coll_name, {})
        if count > 0:
            deleted[coll_name] = count
    
    # Master data collections - clear completely
    master_collections = [
        "products",
        "categories",
        "vendors",
    ]
    for coll_name in master_collections:
        count = repo.delete_many(coll_name, {})
        if count > 0:
            deleted[coll_name] = count
    
    # Ledger collections - clear completely
    ledger_collections = [
        "stock_ledger",
        "financial_ledger",
        "ledger",
        "sessions",
    ]
    for coll_name in ledger_collections:
        count = repo.delete_many(coll_name, {})
        if count > 0:
            deleted[coll_name] = count
    
    # Remove all non-admin users
    count = repo.delete_users_except(settings.admin_username)
    if count > 0:
        deleted["users"] = count
    
    # Clear user-role mappings for non-admin users
    count = repo.delete_user_role_mappings_except(settings.admin_username)
    if count > 0:
        deleted["user_role_mappings"] = count
    
    # Clear mapping collections
    mapping_collections = [
        "role_permissions",
        "role_functionality_mappings",
    ]
    for coll_name in mapping_collections:
        count = repo.delete_many(coll_name, {})
        if count > 0:
            deleted[coll_name] = count
    
    # Clear asset collections
    count = repo.delete_many("company_assets", {})
    if count > 0:
        deleted["company_assets"] = count
    
    # Reset counters collection for ID generation sequences
    count = repo.delete_many("counters", {})
    if count > 0:
        deleted["counters"] = count
    
    # Remove sample index file if it exists
    if os.path.exists(_INDEX_FILE):
        os.remove(_INDEX_FILE)
    
    total_deleted = sum(deleted.values())
    return {
        "message": f"All sample data discarded. Admin user preserved. Total records deleted: {total_deleted}",
        "deleted": deleted,
        "preserved_admin": settings.admin_username,
    }
