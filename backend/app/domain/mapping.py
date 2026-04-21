"""Entity field mapping matrix for Phase 1 model-layer alignment.

Each mapping is a list of FieldMap entries with three columns:
  api_field     — field name in the Pydantic API schema / JSON response
  domain_field  — field name on the domain entity (entities.py)
  mongo_field   — field name in the MongoDB document

MySQL and SQL Server column names will be added in Phases 6 and 7 respectively.
Until then, the placeholder value is "" (empty string = not yet defined).

Usage (runtime):
    from app.domain.mapping import build_storage_to_domain, build_domain_to_api

    domain_dict = build_storage_to_domain(mongo_doc, USER_MATRIX)
    api_dict    = build_domain_to_api(domain_dict, USER_MATRIX)
"""
from typing import NamedTuple


class FieldMap(NamedTuple):
    """Three-column field mapping for a single attribute of an aggregate."""
    api_field:    str   # Pydantic / JSON response key
    domain_field: str   # entity dataclass field name
    mongo_field:  str   # MongoDB document key


# ── User ──────────────────────────────────────────────────────────────────────
USER_MATRIX: list[FieldMap] = [
    FieldMap("id",                  "id",                   "_id"),
    FieldMap("username",            "username",             "username"),
    FieldMap("email",               "email",                "email"),
    # password_hash is never exposed via API; api_field intentionally blank
    FieldMap("",                    "password_hash",        "password_hash"),
    FieldMap("role",                "role",                 "role"),
    FieldMap("full_name",           "full_name",            "full_name"),
    FieldMap("phone",               "phone",                "phone"),
    FieldMap("address",             "address",              "address"),
    FieldMap("dob",                 "dob",                  "dob"),
    FieldMap("sex",                 "sex",                  "sex"),
    FieldMap("marital_status",      "marital_status",       "marital_status"),
    FieldMap("address_data",        "address_data",         "address_data"),
    FieldMap("saved_payment_data",  "saved_payment_data",   "saved_payment_data"),
    FieldMap("phone_verified",      "phone_verified",       "phone_verified"),
    FieldMap("email_verified",      "email_verified",       "email_verified"),
    FieldMap("is_active",           "is_active",            "is_active"),
    FieldMap("created_at",          "created_at",           "created_at"),
    FieldMap("updated_at",          "updated_at",           "updated_at"),
]

# ── Session ───────────────────────────────────────────────────────────────────
SESSION_MATRIX: list[FieldMap] = [
    FieldMap("id",              "id",               "_id"),
    FieldMap("username",        "username",         "username"),
    FieldMap("client_ip",       "client_ip",        "client_ip"),
    FieldMap("client_mac",      "client_mac",       "client_mac"),
    FieldMap("session_token",   "session_token",    "session_token"),
    FieldMap("created_at",      "created_at",       "created_at"),
    FieldMap("expires_at",      "expires_at",       "expires_at"),
    FieldMap("last_activity",   "last_activity",    "last_activity"),
]

# ── Product ───────────────────────────────────────────────────────────────────
PRODUCT_MATRIX: list[FieldMap] = [
    FieldMap("id",              "id",               "_id"),
    FieldMap("name",            "name",             "name"),
    FieldMap("sku",             "sku",              "sku"),
    FieldMap("barcode",         "barcode",          "barcode"),
    FieldMap("stock_price",     "stock_price",      "stock_price"),
    FieldMap("sell_price",      "sell_price",       "sell_price"),
    FieldMap("description",     "description",      "description"),
    FieldMap("category",        "category",         "category"),
    FieldMap("discount",        "discount",         "discount"),
    FieldMap("discount_value",  "discount_value",   "discount_value"),
    FieldMap("discount_type",   "discount_type",    "discount_type"),
    FieldMap("stock_quantity",  "stock_quantity",   "stock_quantity"),
    FieldMap("gst_rate",        "gst_rate",         "gst_rate"),
    FieldMap("image_media_ids", "image_media_ids",  "image_media_ids"),
    FieldMap("video_media_ids", "video_media_ids",  "video_media_ids"),
    FieldMap("created_at",      "created_at",       "created_at"),
    FieldMap("updated_at",      "updated_at",       "updated_at"),
]

# ── Category ──────────────────────────────────────────────────────────────────
CATEGORY_MATRIX: list[FieldMap] = [
    FieldMap("id",              "id",               "_id"),
    FieldMap("name",            "name",             "name"),
    FieldMap("description",     "description",      "description"),
    FieldMap("discount_type",   "discount_type",    "discount_type"),
    FieldMap("discount_value",  "discount_value",   "discount_value"),
    FieldMap("created_at",      "created_at",       "created_at"),
]

# ── Vendor ────────────────────────────────────────────────────────────────────
VENDOR_MATRIX: list[FieldMap] = [
    FieldMap("id",              "id",               "_id"),
    FieldMap("name",            "name",             "name"),
    FieldMap("email",           "email",            "email"),
    FieldMap("phone",           "phone",            "phone"),
    FieldMap("address",         "address",          "address"),
    FieldMap("gst_number",      "gst_number",       "gst_number"),
    FieldMap("bank_details",    "bank_details",     "bank_details"),
    FieldMap("created_at",      "created_at",       "created_at"),
    FieldMap("updated_at",      "updated_at",       "updated_at"),
]

# ── Cart items (embedded in cart document) ────────────────────────────────────
CART_ITEM_MATRIX: list[FieldMap] = [
    FieldMap("product_id",      "product_id",       "product_id"),
    FieldMap("product_name",    "product_name",     "product_name"),
    FieldMap("product_spec",    "product_spec",     "product_spec"),
    FieldMap("quantity",        "quantity",         "quantity"),
    FieldMap("price",           "price",            "price"),
    FieldMap("line_subtotal",   "line_subtotal",    "line_subtotal"),
    FieldMap("discount_amount", "discount_amount",  "discount_amount"),
    FieldMap("taxable_amount",  "taxable_amount",   "taxable_amount"),
    FieldMap("gst_amount",      "gst_amount",       "gst_amount"),
    FieldMap("total",           "total",            "total"),
]

# ── Order ─────────────────────────────────────────────────────────────────────
ORDER_MATRIX: list[FieldMap] = [
    FieldMap("id",                  "id",                   "_id"),
    FieldMap("customer_id",         "customer_id",          "customer_id"),
    FieldMap("order_number",        "order_number",         "order_number"),
    FieldMap("cart_quote_id",       "cart_quote_id",        "cart_quote_id"),
    FieldMap("items",               "items",                "items"),
    FieldMap("subtotal",            "subtotal",             "subtotal"),
    FieldMap("total_discount",      "total_discount",       "total_discount"),
    FieldMap("total_gst",           "total_gst",            "total_gst"),
    FieldMap("total",               "total",                "total"),
    FieldMap("payment_method",      "payment_method",       "payment_method"),
    FieldMap("shipping_address",    "shipping_address",     "shipping_address"),
    FieldMap("shipment_date",       "shipment_date",        "shipment_date"),
    FieldMap("status",              "status",               "status"),
    FieldMap("return_reason",       "return_reason",        "return_reason"),
    FieldMap("exchange_order_id",   "exchange_order_id",    "exchange_order_id"),
    FieldMap("created_at",          "created_at",           "created_at"),
    FieldMap("updated_at",          "updated_at",           "updated_at"),
]

# ── Order item (embedded in order document) ───────────────────────────────────
ORDER_ITEM_MATRIX: list[FieldMap] = [
    FieldMap("product_id",      "product_id",       "product_id"),
    FieldMap("product_name",    "product_name",     "product_name"),
    FieldMap("quantity",        "quantity",         "quantity"),
    FieldMap("sell_price",      "sell_price",       "sell_price"),
    FieldMap("line_subtotal",   "line_subtotal",    "line_subtotal"),
    FieldMap("discount_amount", "discount_amount",  "discount_amount"),
    FieldMap("taxable_amount",  "taxable_amount",   "taxable_amount"),
    FieldMap("gst_amount",      "gst_amount",       "gst_amount"),
    FieldMap("total",           "total",            "total"),
]

# ── Saved product ─────────────────────────────────────────────────────────────
SAVED_PRODUCT_MATRIX: list[FieldMap] = [
    FieldMap("id",              "id",               "_id"),
    FieldMap("customer_id",     "customer_id",      "customer_id"),
    FieldMap("product_id",      "product_id",       "product_id"),
    FieldMap("saved_price",     "saved_price",      "saved_price"),
    FieldMap("created_at",      "created_at",       "created_at"),
]

# ── Stock ledger ──────────────────────────────────────────────────────────────
STOCK_LEDGER_MATRIX: list[FieldMap] = [
    FieldMap("id",                  "id",               "_id"),
    FieldMap("product_id",          "product_id",       "product_id"),
    FieldMap("transaction_type",    "transaction_type", "transaction_type"),
    FieldMap("quantity",            "quantity",         "quantity"),
    FieldMap("reference",           "reference",        "reference"),
    FieldMap("notes",               "notes",            "notes"),
    FieldMap("created_at",          "created_at",       "created_at"),
]

# ── Financial ledger ──────────────────────────────────────────────────────────
LEDGER_ENTRY_MATRIX: list[FieldMap] = [
    FieldMap("id",                  "id",               "_id"),
    FieldMap("transaction_type",    "transaction_type", "transaction_type"),
    FieldMap("category",            "category",         "category"),
    FieldMap("amount",              "amount",           "amount"),
    FieldMap("reference_id",        "reference_id",     "reference_id"),
    FieldMap("notes",               "notes",            "notes"),
    FieldMap("created_at",          "created_at",       "created_at"),
]

# ── Audit log ─────────────────────────────────────────────────────────────────
AUDIT_LOG_MATRIX: list[FieldMap] = [
    FieldMap("id",          "id",           "_id"),
    FieldMap("action",      "action",       "action"),
    FieldMap("user",        "user",         "user"),
    FieldMap("path",        "path",         "path"),
    FieldMap("details",     "details",      "details"),
    FieldMap("immutable",   "immutable",    "immutable"),
    FieldMap("created_at",  "created_at",   "created_at"),
]

# ── Convenience index: all matrices (for cross-cutting tools / generators) ────
ALL_MATRICES: dict[str, list[FieldMap]] = {
    "user":             USER_MATRIX,
    "session":          SESSION_MATRIX,
    "product":          PRODUCT_MATRIX,
    "category":         CATEGORY_MATRIX,
    "vendor":           VENDOR_MATRIX,
    "cart_item":        CART_ITEM_MATRIX,
    "order":            ORDER_MATRIX,
    "order_item":       ORDER_ITEM_MATRIX,
    "saved_product":    SAVED_PRODUCT_MATRIX,
    "stock_ledger":     STOCK_LEDGER_MATRIX,
    "ledger_entry":     LEDGER_ENTRY_MATRIX,
    "audit_log":        AUDIT_LOG_MATRIX,
}


# ── Runtime helpers ───────────────────────────────────────────────────────────
def build_storage_to_domain(doc: dict, matrix: list[FieldMap]) -> dict:
    """Return domain-keyed dict from a MongoDB storage document.

    Only entries where mongo_field is non-empty are mapped.
    Missing keys in doc default to None.
    """
    return {
        m.domain_field: doc.get(m.mongo_field)
        for m in matrix
        if m.mongo_field
    }


def build_domain_to_api(domain_dict: dict, matrix: list[FieldMap]) -> dict:
    """Return API-keyed dict from a domain-keyed dict.

    Only entries where api_field is non-empty are included
    (fields with blank api_field are internal-only, e.g. password_hash).
    """
    return {
        m.api_field: domain_dict.get(m.domain_field)
        for m in matrix
        if m.api_field
    }


# Backward-compatibility aliases for any code that referenced the old plain dicts.
USER_FIELD_MAP    = {m.mongo_field: m.domain_field for m in USER_MATRIX    if m.mongo_field}
PRODUCT_FIELD_MAP = {m.mongo_field: m.domain_field for m in PRODUCT_MATRIX if m.mongo_field}
ORDER_FIELD_MAP   = {m.mongo_field: m.domain_field for m in ORDER_MATRIX   if m.mongo_field}


def map_storage_to_domain(doc: dict, field_map: dict[str, str]) -> dict:
    """Legacy helper — maps storage-keyed doc to domain-keyed dict via a plain dict.

    Prefer build_storage_to_domain() with a matrix for new code.
    """
    return {domain_key: doc.get(storage_key) for storage_key, domain_key in field_map.items()}
