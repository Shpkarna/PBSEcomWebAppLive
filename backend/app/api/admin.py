"""Admin API: sample data load/discard and admin-only CRUD."""
import json
import os
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional

from app.database import get_collection
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
async def load_sample_data(_: dict = Depends(require_role(["admin"]))):
    """Load sample data into all collections. Admin only. Dev/test use."""
    if settings.package_option == "prod":
        raise HTTPException(status_code=403, detail="Sample data tools are disabled in production")
    now = get_now()
    index: dict = {}

    cats = get_collection("categories")
    cat_ids = []
    for cat in SAMPLE_CATEGORIES:
        existing = cats.find_one({"name": cat["name"]})
        if not existing:
            res = cats.insert_one({**cat, "created_at": now})
            cat_ids.append(str(res.inserted_id))
    index["categories"] = cat_ids

    vend = get_collection("vendors")
    vend_ids = []
    for v in SAMPLE_VENDORS:
        existing = vend.find_one({"email": v["email"]})
        if not existing:
            res = vend.insert_one({**v, "created_at": now})
            vend_ids.append(str(res.inserted_id))
    index["vendors"] = vend_ids

    users = get_collection("users")
    user_ids = []
    for u in SAMPLE_USERS:
        existing = users.find_one({"username": u["username"]})
        if not existing:
            rec = {**u, "password_hash": hash_password("Sample@123"),
                   "created_at": now, "updated_at": now}
            res = users.insert_one(rec)
            user_ids.append(str(res.inserted_id))
    index["users"] = user_ids

    prods = get_collection("products")
    prod_ids = []
    for p in SAMPLE_PRODUCTS:
        existing = prods.find_one({"sku": p["sku"]})
        if not existing:
            res = prods.insert_one({**p, "created_at": now, "updated_at": now})
            prod_ids.append(str(res.inserted_id))
    index["products"] = prod_ids

    sample_customer = users.find_one({"username": "customer1"})
    orders = get_collection("orders")
    order_ids = []
    if sample_customer:
        for o in SAMPLE_ORDERS:
            # Enrich order items with product_id from DB
            enriched_items = []
            for oi in o.get("items", []):
                item_copy = {**oi}
                if "product_id" not in item_copy:
                    prod = prods.find_one({"name": oi.get("product_name", "")})
                    if prod:
                        item_copy["product_id"] = str(prod["_id"])
                    else:
                        item_copy["product_id"] = "unknown"
                enriched_items.append(item_copy)
            order_doc = {**o, "items": enriched_items,
                         "customer_id": str(sample_customer["_id"]),
                         "created_at": now, "updated_at": now}
            res = orders.insert_one(order_doc)
            order_ids.append(str(res.inserted_id))
    index["orders"] = order_ids

    # Cart items (linked to sample customer)
    cart_col = get_collection("cart")
    cart_ids = []
    if sample_customer:
        for ci in SAMPLE_CART_ITEMS:
            prod = prods.find_one({"sku": ci["product_sku"]})
            if prod:
                rec = {"user_id": str(sample_customer["_id"]),
                       "product_id": str(prod["_id"]),
                       "product_name": prod["name"],
                       "quantity": ci["quantity"],
                       "price": prod["sell_price"],
                       "gst_rate": prod.get("gst_rate", 0.18),
                       "created_at": now, "updated_at": now}
                res = cart_col.insert_one(rec)
                cart_ids.append(str(res.inserted_id))
    index["cart"] = cart_ids

    # Saved products (linked to sample customer)
    saved_col = get_collection("saved_products")
    saved_ids = []
    if sample_customer:
        for sp in SAMPLE_SAVED_PRODUCTS:
            prod = prods.find_one({"sku": sp["product_sku"]})
            if prod:
                rec = {"user_id": str(sample_customer["_id"]),
                       "product_id": str(prod["_id"]), "created_at": now}
                res = saved_col.insert_one(rec)
                saved_ids.append(str(res.inserted_id))
    index["saved_products"] = saved_ids

    # Stock ledger
    stock_col = get_collection("stock_ledger")
    stock_ids = []
    for sl in SAMPLE_STOCK_LEDGER:
        prod = prods.find_one({"sku": sl["product_sku"]})
        if prod:
            rec = {"product_id": str(prod["_id"]),
                   "transaction_type": sl["transaction_type"],
                   "quantity": sl["quantity"],
                   "reference": sl["reference"],
                   "notes": sl.get("notes", ""),
                   "created_at": now}
            res = stock_col.insert_one(rec)
            stock_ids.append(str(res.inserted_id))
    index["stock_ledger"] = stock_ids

    # Ledger
    ledger_col = get_collection("ledger")
    ledger_ids = []
    for le in SAMPLE_LEDGER:
        rec = {**le, "created_at": now}
        res = ledger_col.insert_one(rec)
        ledger_ids.append(str(res.inserted_id))
    index["ledger"] = ledger_ids

    # Contact inquiries
    contact_col = get_collection("contact_inquiries")
    contact_ids = []
    for ci in SAMPLE_CONTACT_INQUIRIES:
        rec = {**ci, "created_at": now, "status": "new"}
        res = contact_col.insert_one(rec)
        contact_ids.append(str(res.inserted_id))
    index["contact_inquiries"] = contact_ids

    # User-role mappings
    urm_col = get_collection("user_role_mappings")
    urm_ids = []
    for urm in SAMPLE_USER_ROLE_MAPPINGS:
        u = users.find_one({"username": urm["username"]})
        if u:
            existing = urm_col.find_one({"username": urm["username"]})
            if not existing:
                rec = {"user_id": str(u["_id"]), "username": urm["username"],
                       "role": urm["role"], "created_at": now}
                res = urm_col.insert_one(rec)
                urm_ids.append(str(res.inserted_id))
    index["user_role_mappings"] = urm_ids

    # Role-functionality mappings
    rfm_col = get_collection("role_functionality_mappings")
    rfm_ids = []
    for rfm in SAMPLE_ROLE_FUNCTIONALITY_MAPPINGS:
        existing = rfm_col.find_one({"role": rfm["role"],
                                     "functionality_code": rfm["functionality_code"]})
        if not existing:
            rec = {**rfm, "created_at": now}
            res = rfm_col.insert_one(rec)
            rfm_ids.append(str(res.inserted_id))
    index["role_functionality_mappings"] = rfm_ids

    _save_index(index)
    total = sum(len(v) for v in index.values())
    return {"message": f"Sample data loaded: {total} records", "summary": index}


@router.post("/discard-sample-data")
async def discard_sample_data(_: dict = Depends(require_role(["admin"]))):
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
        coll = get_collection(coll_name)
        res = coll.delete_many({})
        if res.deleted_count > 0:
            deleted[coll_name] = res.deleted_count
    
    # Master data collections - clear completely
    master_collections = [
        "products",
        "categories",
        "vendors",
    ]
    for coll_name in master_collections:
        coll = get_collection(coll_name)
        res = coll.delete_many({})
        if res.deleted_count > 0:
            deleted[coll_name] = res.deleted_count
    
    # Ledger collections - clear completely
    ledger_collections = [
        "stock_ledger",
        "financial_ledger",
        "ledger",
        "sessions",
    ]
    for coll_name in ledger_collections:
        coll = get_collection(coll_name)
        res = coll.delete_many({})
        if res.deleted_count > 0:
            deleted[coll_name] = res.deleted_count
    
    # Remove all non-admin users
    users_coll = get_collection("users")
    res = users_coll.delete_many({"username": {"$ne": settings.admin_username}})
    if res.deleted_count > 0:
        deleted["users"] = res.deleted_count
    
    # Clear user-role mappings for non-admin users
    urm_coll = get_collection("user_role_mappings")
    res = urm_coll.delete_many({"username": {"$ne": settings.admin_username}})
    if res.deleted_count > 0:
        deleted["user_role_mappings"] = res.deleted_count
    
    # Clear mapping collections
    mapping_collections = [
        "role_permissions",
        "role_functionality_mappings",
    ]
    for coll_name in mapping_collections:
        coll = get_collection(coll_name)
        res = coll.delete_many({})
        if res.deleted_count > 0:
            deleted[coll_name] = res.deleted_count
    
    # Clear asset collections
    assets_coll = get_collection("company_assets")
    res = assets_coll.delete_many({})
    if res.deleted_count > 0:
        deleted["company_assets"] = res.deleted_count
    
    # Reset counters collection for ID generation sequences
    counters_coll = get_collection("counters")
    res = counters_coll.delete_many({})
    if res.deleted_count > 0:
        deleted["counters"] = res.deleted_count
    
    # Remove sample index file if it exists
    if os.path.exists(_INDEX_FILE):
        os.remove(_INDEX_FILE)
    
    total_deleted = sum(deleted.values())
    return {
        "message": f"All sample data discarded. Admin user preserved. Total records deleted: {total_deleted}",
        "deleted": deleted,
        "preserved_admin": settings.admin_username,
    }
