"""Repository contract for cart/order persistence gateway.

Phase 2 introduced this bridge contract to expose backing stores for cart/order APIs.
Phase 3 extends it with domain-oriented operations so orchestration can live in
services while preserving runtime behavior.
"""
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Any, Optional


class OrderCartRepository(ABC):
    """Storage-agnostic gateway for cart and order route persistence needs."""

    @abstractmethod
    def transaction(self) -> AbstractContextManager[None]:
        """Return a context manager for atomic multi-step write operations."""

    @abstractmethod
    def find_user_by_username(self, username: str) -> dict | None:
        """Return user document by username."""

    @abstractmethod
    def find_product_by_id(self, product_id: str) -> dict | None:
        """Return product document by string id."""

    @abstractmethod
    def find_cart_item(self, user_id: str, session_id: str, product_id: str) -> dict | None:
        """Return cart line for user/session/product if present."""

    @abstractmethod
    def find_any_cart_item(self, user_id: str, session_id: str) -> dict | None:
        """Return any cart line for user/session."""

    @abstractmethod
    def update_cart_item_quantity(self, cart_item_id: Any, quantity_delta: int) -> None:
        """Increment existing cart item quantity and set updated_at."""

    @abstractmethod
    def backfill_cart_quote_id(self, user_id: str, session_id: str, cart_quote_id: str) -> None:
        """Populate missing cart_quote_id for existing session cart rows."""

    @abstractmethod
    def insert_cart_item(self, doc: dict) -> None:
        """Insert new cart row."""

    @abstractmethod
    def list_cart_items(self, user_id: str, session_id: str) -> list[dict]:
        """Return all cart rows for user/session."""

    @abstractmethod
    def remove_cart_item(self, user_id: str, session_id: str, product_id: str) -> int:
        """Delete one cart row and return deleted count."""

    @abstractmethod
    def clear_session_cart(self, user_id: str, session_id: str) -> None:
        """Delete all cart rows for user/session."""

    @abstractmethod
    def acquire_checkout_lock(self, cart_quote_id: str, session_id: str, ttl_minutes: int) -> None:
        """Acquire or refresh checkout lock for the session/cart_quote_id."""

    @abstractmethod
    def release_checkout_lock(self, cart_quote_id: str) -> None:
        """Release checkout lock for cart_quote_id."""

    @abstractmethod
    def set_customer_business_id(self, user_id: Any, customer_id: str) -> None:
        """Persist generated customer business id for user."""

    @abstractmethod
    def insert_payment_record(self, doc: dict) -> None:
        """Insert payment tracking record."""

    @abstractmethod
    def find_pending_razorpay_payment(self, razorpay_order_id: str, username: str) -> dict | None:
        """Return pending Razorpay payment record for order and username."""

    @abstractmethod
    def mark_payment_verified(self, payment_id: Any, razorpay_payment_id: str, razorpay_signature: str) -> None:
        """Mark payment record as verified."""

    @abstractmethod
    def decrement_product_stock_if_available(self, product_id: str, quantity: int) -> bool:
        """Decrease stock if sufficient quantity exists; return success flag."""

    @abstractmethod
    def insert_stock_ledger_row(self, doc: dict) -> None:
        """Insert stock ledger row."""

    @abstractmethod
    def insert_order(self, doc: dict) -> Any:
        """Insert order and return inserted id."""

    @abstractmethod
    def update_user_address_data_if_changed(self, user_id: Any, current_address: dict, new_address: dict) -> None:
        """Persist address_data only when changed."""

    @abstractmethod
    def insert_sales_ledger_row(self, doc: dict) -> None:
        """Insert sales ledger row."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Categories
    # ------------------------------------------------------------------

    @abstractmethod
    def list_categories(self, skip: int = 0, limit: int = 50) -> list[dict]:
        """Return categories with pagination."""

    @abstractmethod
    def find_category_by_name(self, name: str) -> dict | None:
        """Return category document matching name exactly."""

    @abstractmethod
    def create_category(self, doc: dict) -> dict:
        """Insert category and return stored document with id field."""

    @abstractmethod
    def get_category(self, cat_id: str) -> dict | None:
        """Return category by string id. Return None for unknown/invalid id."""

    @abstractmethod
    def update_category(self, cat_id: str, updates: dict) -> int:
        """Apply partial updates to category. Return matched_count."""

    @abstractmethod
    def delete_category(self, cat_id: str) -> int:
        """Delete category by id. Return deleted_count."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Vendors
    # ------------------------------------------------------------------

    @abstractmethod
    def list_vendors(self, skip: int = 0, limit: int = 50) -> list[dict]:
        """Return vendors with pagination."""

    @abstractmethod
    def find_vendor_by_email(self, email: str) -> dict | None:
        """Return vendor document matching email."""

    @abstractmethod
    def create_vendor(self, doc: dict) -> dict:
        """Insert vendor and return stored document with id field."""

    @abstractmethod
    def get_vendor(self, vendor_id: str) -> dict | None:
        """Return vendor by string id. Return None for unknown/invalid id."""

    @abstractmethod
    def update_vendor(self, vendor_id: str, updates: dict) -> int:
        """Apply partial updates to vendor. Return matched_count."""

    @abstractmethod
    def delete_vendor(self, vendor_id: str) -> int:
        """Delete vendor by id. Return deleted_count."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Contact Inquiries
    # ------------------------------------------------------------------

    @abstractmethod
    def create_contact_inquiry(self, doc: dict) -> dict:
        """Insert contact inquiry and return stored document with id field."""

    @abstractmethod
    def list_contact_inquiries(
        self, skip: int = 0, limit: int = 50, status_filter: str | None = None
    ) -> list[dict]:
        """Return contact inquiries, newest first, with optional status filter."""

    @abstractmethod
    def get_contact_inquiry(self, inquiry_id: str) -> dict | None:
        """Return contact inquiry by string id."""

    @abstractmethod
    def update_contact_inquiry(self, inquiry_id: str, updates: dict) -> int:
        """Apply partial updates to inquiry. Return matched_count."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Stock Ledger
    # ------------------------------------------------------------------

    @abstractmethod
    def list_stock_ledger(
        self,
        product_id_filter: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """Return stock ledger entries, newest first, with optional product filter."""

    @abstractmethod
    def add_stock_entry(self, entry_doc: dict) -> dict:
        """Insert stock ledger entry and return stored document with id field."""

    @abstractmethod
    def get_stock_entry(self, entry_id: str) -> dict | None:
        """Return stock ledger entry by string id."""

    @abstractmethod
    def update_product_stock(self, product_id: str, new_qty: int) -> None:
        """Set stock_quantity to new_qty for the given product."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Saved Products
    # ------------------------------------------------------------------

    @abstractmethod
    def find_saved_product(self, user_id: str, product_id: str) -> dict | None:
        """Return saved_product row for user/product if present."""

    @abstractmethod
    def create_saved_product(self, doc: dict) -> dict:
        """Insert saved product record and return stored document."""

    @abstractmethod
    def list_saved_products_for_user(self, user_id: str) -> list[dict]:
        """Return all saved product rows for a user."""

    @abstractmethod
    def delete_saved_product(self, user_id: str, product_id: str) -> int:
        """Remove saved product for user/product. Return deleted_count."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Orders (admin listing)
    # ------------------------------------------------------------------

    @abstractmethod
    def list_orders_filtered(
        self,
        query: dict,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """Return orders matching query, sorted newest first."""

    @abstractmethod
    def aggregate_orders(self, pipeline: list) -> list[dict]:
        """Run aggregation pipeline against orders collection."""

    @abstractmethod
    def search_sales_orders(
        self,
        *,
        order_id: Optional[str] = None,
        order_number: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict], int]:
        """Search and paginate sales orders. Return (items, total_count)."""

    @abstractmethod
    def update_order_status(self, order_id: str, new_status: str, updated_at: Optional[datetime] = None) -> int:
        """Update order status field. Return matched_count."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Company Config / Assets / Gateways
    # ------------------------------------------------------------------

    @abstractmethod
    def find_company_config(self, config_id: str) -> dict | None:
        """Return company config document by configId."""

    @abstractmethod
    def upsert_company_config(self, config_id: str, updates: dict) -> None:
        """Upsert a company config document identified by configId."""

    @abstractmethod
    def get_company_assets(self, asset_key: str = "company_image") -> dict | None:
        """Return company assets document by asset_key."""

    @abstractmethod
    def upsert_company_asset(self, asset_key: str, asset_data: dict) -> None:
        """Upsert company asset document by asset_key."""

    @abstractmethod
    def find_payment_gateway(self, gateway_id: str) -> dict | None:
        """Return payment gateway config by gatewayId."""

    @abstractmethod
    def upsert_payment_gateway(self, gateway_id: str, updates: dict) -> None:
        """Upsert payment gateway config document."""

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Admin / Data Sync generic helpers
    # ------------------------------------------------------------------

    @abstractmethod
    def find_one(self, collection_name: str, filter_doc: dict) -> dict | None:
        """Find a single document in a named collection by filter."""

    @abstractmethod
    def insert_one(self, collection_name: str, doc: dict) -> dict:
        """Insert document into named collection. Return stored doc with 'id'."""

    @abstractmethod
    def update_one(self, collection_name: str, filter_doc: dict, update_doc: dict, upsert: bool = False) -> int:
        """Update one matching document. Return matched_count."""

    @abstractmethod
    def delete_many(self, collection_name: str, filter_doc: dict) -> int:
        """Delete matching documents from named collection. Return deleted_count."""

    @abstractmethod
    def delete_users_except(self, keep_username: str) -> int:
        """Delete all users except the one with given username. Return deleted_count."""

    @abstractmethod
    def delete_user_role_mappings_except(self, keep_username: str) -> int:
        """Delete all user-role mappings except for given username. Return deleted_count."""

    @abstractmethod
    def find_many(
        self,
        collection_name: str,
        filter_doc: dict,
        projection: dict | None = None,
    ) -> list[dict]:
        """Return all matching documents from a named collection."""

    # ------------------------------------------------------------------
    # Phase 3: Named operations — Orders (customer-facing)
    # ------------------------------------------------------------------

    @abstractmethod
    def list_user_orders(
        self, customer_keys: list[str], skip: int = 0, limit: int = 10
    ) -> list[dict]:
        """Return orders for a user identified by customer key(s), newest first."""

    @abstractmethod
    def find_order_by_id(self, order_id: str) -> dict | None:
        """Return order document by string id, or None for invalid/missing id."""

    @abstractmethod
    def update_order(self, order_id: str, updates: dict) -> int:
        """Update order fields by string id. Return matched_count."""

    @abstractmethod
    def create_order(self, doc: dict) -> dict:
        """Insert order and return stored document with 'id' string field."""

    @abstractmethod
    def increment_product_stock(self, product_id: str, qty_delta: int) -> None:
        """Atomically adjust product stock_quantity by *qty_delta*."""

    # ------------------------------------------------------------------
    # Phase 4: Named operations — Cart cleanup
    # ------------------------------------------------------------------

    @abstractmethod
    def distinct_cart_session_ids(self) -> list[str]:
        """Return distinct session_ids present in the cart collection."""

    @abstractmethod
    def list_cart_items_by_session(self, session_id: str) -> list[dict]:
        """Return all cart items for the given session_id."""

    @abstractmethod
    def delete_checkout_locks_by_quote_ids(self, quote_ids: list[str]) -> int:
        """Delete checkout locks matching any of the given cart_quote_ids. Return deleted_count."""

    @abstractmethod
    def delete_cart_items_by_session(self, session_id: str) -> int:
        """Delete all cart items for the given session_id. Return deleted_count."""
