"""Shared MySQL metadata and value-conversion helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import json
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class TableSpec:
    """Physical-table mapping for a logical collection name."""

    table_name: str
    columns: tuple[str, ...]
    id_column: str = "id"
    json_column: str | None = "payload_json"
    bool_columns: tuple[str, ...] = ()
    decimal_columns: tuple[str, ...] = ()
    binary_columns: tuple[str, ...] = ()


MYSQL_TABLE_SPECS: dict[str, TableSpec] = {
    "users": TableSpec(
        table_name="users",
        columns=(
            "id", "username", "email", "password_hash", "full_name", "phone", "dob", "sex",
            "marital_status", "address", "role", "customer_id", "is_active", "phone_verified",
            "email_verified", "created_at", "updated_at",
        ),
        bool_columns=("is_active", "phone_verified", "email_verified"),
    ),
    "sessions": TableSpec(
        table_name="sessions",
        columns=(
            "id", "username", "client_ip", "client_mac", "access_token", "token_expires_at",
            "created_at", "expires_at", "last_activity",
        ),
    ),
    "email_verifications": TableSpec(
        table_name="email_verifications",
        columns=("id", "username", "token", "verified", "verified_at", "expires_at", "created_at"),
        bool_columns=("verified",),
    ),
    "otp_records": TableSpec(
        table_name="otp_records",
        columns=(
            "id", "phone", "purpose", "otp", "created_at", "expires_at", "verified", "verified_at",
            "used", "used_at", "verification_attempts",
        ),
        bool_columns=("verified", "used"),
    ),
    "products": TableSpec(
        table_name="products",
        columns=(
            "id", "sku", "name", "barcode", "description", "category", "stock_price", "sell_price",
            "discount", "discount_value", "discount_type", "stock_quantity", "gst_rate", "is_active",
            "created_at", "updated_at",
        ),
        bool_columns=("is_active",),
        decimal_columns=("stock_price", "sell_price", "discount_value", "gst_rate"),
    ),
    "product_media": TableSpec(
        table_name="product_media",
        columns=(
            "id", "product_id", "filename", "content_type", "media_type", "size", "created_at",
            "created_by", "data",
        ),
        binary_columns=("data",),
    ),
    "cart": TableSpec(
        table_name="cart_items",
        columns=(
            "id", "user_id", "session_id", "product_id", "product_name", "quantity", "price", "gst_rate",
            "cart_quote_id", "created_at", "updated_at",
        ),
        decimal_columns=("price", "gst_rate"),
    ),
    "categories": TableSpec(
        table_name="categories",
        columns=("id", "name", "description", "discount_type", "discount_value", "created_at", "updated_at"),
        decimal_columns=("discount_value",),
    ),
    "orders": TableSpec(
        table_name="orders",
        columns=(
            "id", "customer_id", "order_number", "cart_quote_id", "subtotal", "total_discount",
            "total_gst", "total", "payment_method", "payment_status", "payment_provider",
            "payment_reference", "razorpay_order_id", "status", "created_at", "updated_at",
        ),
        decimal_columns=("subtotal", "total_discount", "total_gst", "total"),
    ),
    "ledger": TableSpec(
        table_name="ledger_entries",
        columns=("id", "transaction_type", "category", "amount", "reference_id", "notes", "created_at"),
        decimal_columns=("amount",),
    ),
    "stock_ledger": TableSpec(
        table_name="stock_ledger",
        columns=("id", "product_id", "transaction_type", "quantity", "reference", "notes", "created_at"),
    ),
    "payments": TableSpec(
        table_name="payments",
        columns=(
            "id", "provider", "status", "username", "customer_id", "payment_method", "razorpay_order_id",
            "razorpay_payment_id", "razorpay_signature", "amount", "currency", "receipt", "created_at",
            "updated_at",
        ),
    ),
    "checkout_locks": TableSpec(
        table_name="checkout_locks",
        columns=("cart_quote_id", "session_id", "expires_at", "created_at", "updated_at"),
        id_column="cart_quote_id",
    ),
    "vendors": TableSpec(
        table_name="vendors",
        columns=(
            "id", "name", "email", "phone", "address", "gst_number", "bank_details", "created_at",
            "updated_at",
        ),
    ),
    "saved_products": TableSpec(
        table_name="saved_products",
        columns=("id", "customer_id", "product_id", "saved_price", "created_at", "updated_at"),
        decimal_columns=("saved_price",),
    ),
    "contact_inquiries": TableSpec(
        table_name="contact_inquiries",
        columns=("id", "name", "email", "phone", "subject", "message", "status", "created_at", "updated_at"),
    ),
    "company_assets": TableSpec(
        table_name="company_assets",
        columns=(
            "asset_key", "filename", "extension", "content_type", "size", "data", "updated_at",
            "updated_by", "created_at",
        ),
        id_column="asset_key",
        binary_columns=("data",),
    ),
    "company_config": TableSpec(
        table_name="company_config",
        columns=("configId", "created_at", "updated_at"),
        id_column="configId",
    ),
    "payment_gateways": TableSpec(
        table_name="payment_gateways",
        columns=("gatewayId", "created_at", "updated_at"),
        id_column="gatewayId",
    ),
    "data_sync_jobs": TableSpec(
        table_name="data_sync_jobs",
        columns=(
            "id", "entity", "job_type", "status", "requested_by", "source_filename", "created_at",
            "updated_at", "started_at", "finished_at", "processed_rows", "success_rows", "failed_rows",
        ),
    ),
    "role_permissions": TableSpec(
        table_name="role_permissions",
        columns=("role", "updated_at"),
        id_column="role",
    ),
    "role_functionality_mappings": TableSpec(
        table_name="role_functionality_mappings",
        columns=("id", "role", "functionality_code", "created_at"),
    ),
    "user_role_mappings": TableSpec(
        table_name="user_role_mappings",
        columns=("id", "username", "role", "updated_at"),
    ),
    "counters": TableSpec(
        table_name="counters",
        columns=("counter_key", "seq", "updated_at"),
        id_column="counter_key",
    ),
    "audit_logs": TableSpec(
        table_name="audit_logs",
        columns=("id", "action", "user", "path", "immutable", "created_at"),
        bool_columns=("immutable",),
    ),
}


NULL_IF_EMPTY_COLUMNS = {
    "email",
    "phone",
    "customer_id",
    "razorpay_order_id",
    "razorpay_payment_id",
    "payment_reference",
    "receipt",
    "token_expires_at",
}


def generate_id() -> str:
    """Return a storage-agnostic string identifier."""
    return str(uuid4())


def normalize_datetime(value: datetime | None) -> datetime | None:
    """Convert timezone-aware datetimes to naive UTC for MySQL DATETIME columns."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def normalize_json_value(value: Any) -> Any:
    """Convert Python values into JSON-serializable equivalents."""
    if isinstance(value, dict):
        return {key: normalize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_json_value(item) for item in value]
    if isinstance(value, datetime):
        normalized = normalize_datetime(value)
        return normalized.isoformat() if normalized is not None else None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    return value


def dumps_json(value: Any) -> str | None:
    """Serialize a Python value to JSON text for LONGTEXT/JSON columns."""
    if value in (None, {}, []):
        return None
    return json.dumps(normalize_json_value(value), separators=(",", ":"), ensure_ascii=True)


def loads_json(value: str | bytes | None) -> Any:
    """Deserialize JSON text, defaulting to an empty dict."""
    if value in (None, "", b""):
        return {}
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return json.loads(value)


def normalize_scalar_for_storage(column: str, value: Any) -> Any:
    """Normalize a scalar value before binding it into a MySQL statement."""
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, Decimal):
        value = Decimal(str(value))
    if isinstance(value, datetime):
        value = normalize_datetime(value)
    if column in NULL_IF_EMPTY_COLUMNS and value == "":
        return None
    return value


def normalize_document_value(value: Any) -> Any:
    """Normalize MySQL-returned values for API/service consumption."""
    if isinstance(value, dict):
        return {key: normalize_document_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_document_value(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    return value