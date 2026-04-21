"""MySQL-backed cart/order gateway repository."""
from __future__ import annotations

from datetime import datetime, timedelta

from app.data.mysql_client import mysql_connection, mysql_transaction
from app.data.repositories.mysql_base import MySQLRepositoryBase
from app.domain.contracts.order_cart_repository import OrderCartRepository


class MySQLOrderCartRepository(MySQLRepositoryBase, OrderCartRepository):
    """MySQL implementation for cart, order, admin, and config persistence."""

    def transaction(self):
        return mysql_transaction()

    def _first_doc(
        self,
        collection_name: str,
        filter_doc: dict,
        *,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict | None:
        docs = self.find_many_docs(
            collection_name,
            filter_doc,
            order_by=order_by,
            descending=descending,
            limit=1,
        )
        return docs[0] if docs else None

    def find_user_by_username(self, username: str) -> dict | None:
        return self.find_one_doc("users", {"username": username})

    def find_product_by_id(self, product_id: str) -> dict | None:
        return self.find_one_doc("products", {"id": product_id})

    def find_cart_item(self, user_id: str, session_id: str, product_id: str) -> dict | None:
        return self.find_one_doc(
            "cart",
            {"user_id": user_id, "session_id": session_id, "product_id": product_id},
        )

    def find_any_cart_item(self, user_id: str, session_id: str) -> dict | None:
        return self._first_doc("cart", {"user_id": user_id, "session_id": session_id}, order_by="created_at")

    def update_cart_item_quantity(self, cart_item_id, quantity_delta: int) -> None:
        self._execute(
            (
                "UPDATE cart_items SET quantity = quantity + %s, updated_at = %s "
                "WHERE id = %s"
            ),
            [int(quantity_delta), datetime.utcnow(), str(cart_item_id)],
        )

    def backfill_cart_quote_id(self, user_id: str, session_id: str, cart_quote_id: str) -> None:
        self._execute(
            (
                "UPDATE cart_items SET cart_quote_id = %s "
                "WHERE user_id = %s AND session_id = %s "
                "AND (cart_quote_id IS NULL OR cart_quote_id = '')"
            ),
            [cart_quote_id, user_id, session_id],
        )

    def insert_cart_item(self, doc: dict) -> None:
        self.insert_one_doc("cart", doc)

    def list_cart_items(self, user_id: str, session_id: str) -> list[dict]:
        return self.find_many_docs("cart", {"user_id": user_id, "session_id": session_id})

    def remove_cart_item(self, user_id: str, session_id: str, product_id: str) -> int:
        return self.delete_many_docs(
            "cart",
            {"user_id": user_id, "session_id": session_id, "product_id": product_id},
        )

    def clear_session_cart(self, user_id: str, session_id: str) -> None:
        self.delete_many_docs("cart", {"user_id": user_id, "session_id": session_id})

    def acquire_checkout_lock(self, cart_quote_id: str, session_id: str, ttl_minutes: int) -> None:
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=ttl_minutes)
        with mysql_transaction():
            with mysql_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        (
                            "SELECT cart_quote_id, session_id, expires_at FROM checkout_locks "
                            "WHERE cart_quote_id = %s FOR UPDATE"
                        ),
                        [cart_quote_id],
                    )
                    row = cursor.fetchone()
                    if row is None:
                        cursor.execute(
                            (
                                "INSERT INTO checkout_locks (cart_quote_id, session_id, expires_at, created_at, updated_at, payload_json) "
                                "VALUES (%s, %s, %s, %s, %s, NULL)"
                            ),
                            [cart_quote_id, session_id, expires_at, now, now],
                        )
                        return
                    if row.get("session_id") == session_id or row.get("expires_at") < now:
                        cursor.execute(
                            (
                                "UPDATE checkout_locks SET session_id = %s, expires_at = %s, updated_at = %s "
                                "WHERE cart_quote_id = %s"
                            ),
                            [session_id, expires_at, now, cart_quote_id],
                        )
                        return
        raise ValueError("checkout_lock_conflict")

    def release_checkout_lock(self, cart_quote_id: str) -> None:
        self.delete_many_docs("checkout_locks", {"cart_quote_id": cart_quote_id})

    def set_customer_business_id(self, user_id, customer_id: str) -> None:
        self.update_one_doc(
            "users",
            {"id": str(user_id)},
            {"customer_id": customer_id, "updated_at": datetime.utcnow()},
        )

    def insert_payment_record(self, doc: dict) -> None:
        self.insert_one_doc("payments", doc)

    def find_pending_razorpay_payment(self, razorpay_order_id: str, username: str) -> dict | None:
        return self.find_one_doc(
            "payments",
            {
                "provider": "razorpay",
                "status": "created",
                "razorpay_order_id": razorpay_order_id,
                "username": username,
            },
        )

    def mark_payment_verified(self, payment_id, razorpay_payment_id: str, razorpay_signature: str) -> None:
        self.update_one_doc(
            "payments",
            {"id": str(payment_id)},
            {
                "status": "verified",
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
                "updated_at": datetime.utcnow(),
            },
        )

    def decrement_product_stock_if_available(self, product_id: str, quantity: int) -> bool:
        updated = self._execute(
            (
                "UPDATE products SET stock_quantity = stock_quantity - %s, updated_at = %s "
                "WHERE id = %s AND stock_quantity >= %s"
            ),
            [int(quantity), datetime.utcnow(), product_id, int(quantity)],
        )
        return updated > 0

    def insert_stock_ledger_row(self, doc: dict) -> None:
        self.insert_one_doc("stock_ledger", doc)

    def insert_order(self, doc: dict):
        stored = self.insert_one_doc("orders", doc)
        return stored["id"]

    def update_user_address_data_if_changed(self, user_id, current_address: dict, new_address: dict) -> None:
        if new_address != (current_address or {}):
            self.update_one_doc(
                "users",
                {"id": str(user_id)},
                {"address_data": new_address, "updated_at": datetime.utcnow()},
            )

    def insert_sales_ledger_row(self, doc: dict) -> None:
        self.insert_one_doc("ledger", doc)

    def list_categories(self, skip: int = 0, limit: int = 50) -> list[dict]:
        return self.find_many_docs("categories", {}, skip=skip, limit=limit)

    def find_category_by_name(self, name: str) -> dict | None:
        return self.find_one_doc("categories", {"name": name})

    def create_category(self, doc: dict) -> dict:
        return self.insert_one_doc("categories", doc)

    def get_category(self, cat_id: str) -> dict | None:
        return self.find_one_doc("categories", {"id": cat_id})

    def update_category(self, cat_id: str, updates: dict) -> int:
        return self.update_one_doc("categories", {"id": cat_id}, updates)

    def delete_category(self, cat_id: str) -> int:
        return self.delete_many_docs("categories", {"id": cat_id})

    def list_vendors(self, skip: int = 0, limit: int = 50) -> list[dict]:
        return self.find_many_docs("vendors", {}, skip=skip, limit=limit)

    def find_vendor_by_email(self, email: str) -> dict | None:
        return self.find_one_doc("vendors", {"email": email})

    def create_vendor(self, doc: dict) -> dict:
        return self.insert_one_doc("vendors", doc)

    def get_vendor(self, vendor_id: str) -> dict | None:
        return self.find_one_doc("vendors", {"id": vendor_id})

    def update_vendor(self, vendor_id: str, updates: dict) -> int:
        return self.update_one_doc("vendors", {"id": vendor_id}, updates)

    def delete_vendor(self, vendor_id: str) -> int:
        return self.delete_many_docs("vendors", {"id": vendor_id})

    def create_contact_inquiry(self, doc: dict) -> dict:
        return self.insert_one_doc("contact_inquiries", doc)

    def list_contact_inquiries(self, skip: int = 0, limit: int = 50, status_filter: str | None = None) -> list[dict]:
        query = {"status": status_filter} if status_filter else {}
        return self.find_many_docs(
            "contact_inquiries",
            query,
            order_by="created_at",
            descending=True,
            skip=skip,
            limit=limit,
        )

    def get_contact_inquiry(self, inquiry_id: str) -> dict | None:
        return self.find_one_doc("contact_inquiries", {"id": inquiry_id})

    def update_contact_inquiry(self, inquiry_id: str, updates: dict) -> int:
        return self.update_one_doc("contact_inquiries", {"id": inquiry_id}, updates)

    def list_stock_ledger(
        self,
        product_id_filter: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        query = {"product_id": product_id_filter} if product_id_filter else {}
        return self.find_many_docs(
            "stock_ledger",
            query,
            order_by="created_at",
            descending=True,
            skip=skip,
            limit=limit,
        )

    def add_stock_entry(self, entry_doc: dict) -> dict:
        return self.insert_one_doc("stock_ledger", entry_doc)

    def get_stock_entry(self, entry_id: str) -> dict | None:
        return self.find_one_doc("stock_ledger", {"id": entry_id})

    def update_product_stock(self, product_id: str, new_qty: int) -> None:
        self.update_one_doc(
            "products",
            {"id": product_id},
            {"stock_quantity": int(new_qty), "updated_at": datetime.utcnow()},
        )

    def find_saved_product(self, user_id: str, product_id: str) -> dict | None:
        return self.find_one_doc("saved_products", {"customer_id": user_id, "product_id": product_id})

    def create_saved_product(self, doc: dict) -> dict:
        return self.insert_one_doc("saved_products", doc)

    def list_saved_products_for_user(self, user_id: str) -> list[dict]:
        return self.find_many_docs("saved_products", {"customer_id": user_id})

    def delete_saved_product(self, user_id: str, product_id: str) -> int:
        return self.delete_many_docs("saved_products", {"customer_id": user_id, "product_id": product_id})

    def list_orders_filtered(self, query: dict, skip: int = 0, limit: int = 50) -> list[dict]:
        return self.find_many_docs(
            "orders",
            query,
            order_by="created_at",
            descending=True,
            skip=skip,
            limit=limit,
        )

    def aggregate_orders(self, pipeline: list) -> list[dict]:
        raise NotImplementedError("aggregate_orders is not used by the current Phase 6 runtime")

    def search_sales_orders(
        self,
        *,
        order_id=None,
        order_number=None,
        date_from=None,
        date_to=None,
        amount_min=None,
        amount_max=None,
        skip=0,
        limit=20,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        params: list[object] = []

        if order_id:
            pattern = f"%{order_id}%"
            conditions.append("(LOWER(id) LIKE LOWER(%s) OR LOWER(order_number) LIKE LOWER(%s))")
            params.extend([pattern, pattern])
        if order_number:
            conditions.append("LOWER(order_number) LIKE LOWER(%s)")
            params.append(f"%{order_number}%")
        if date_from is not None:
            conditions.append("created_at >= %s")
            params.append(date_from)
        if date_to is not None:
            conditions.append("created_at <= %s")
            params.append(date_to)
        if amount_min is not None:
            conditions.append("total >= %s")
            params.append(amount_min)
        if amount_max is not None:
            conditions.append("total <= %s")
            params.append(amount_max)

        where_sql = " AND ".join(conditions) if conditions else "1=1"
        count_row = self._execute(
            f"SELECT COUNT(*) AS count FROM orders WHERE {where_sql}",
            params,
            fetchone=True,
        ) or {}
        rows = self._execute(
            f"SELECT * FROM orders WHERE {where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            [*params, int(limit), int(skip)],
            fetchall=True,
        )
        spec = self._spec("orders")
        docs = [self._row_to_doc(spec, row) for row in rows or [] if row]
        return docs, int(count_row.get("count", 0))

    def update_order_status(self, order_id: str, new_status: str, updated_at: datetime | None = None) -> int:
        return self.update_one_doc(
            "orders",
            {"id": order_id},
            {"status": new_status, "updated_at": updated_at or datetime.utcnow()},
        )

    def find_company_config(self, config_id: str) -> dict | None:
        return self.find_one_doc("company_config", {"configId": config_id})

    def upsert_company_config(self, config_id: str, updates: dict) -> None:
        existing = self.find_company_config(config_id)
        payload = dict(updates)
        now = datetime.utcnow()
        payload.setdefault("configId", config_id)
        payload.setdefault("updated_at", now)
        if not existing:
            payload.setdefault("created_at", now)
        self.update_one_doc("company_config", {"configId": config_id}, payload, upsert=True)

    def get_company_assets(self, asset_key: str = "company_image") -> dict | None:
        return self.find_one_doc("company_assets", {"asset_key": asset_key})

    def upsert_company_asset(self, asset_key: str, asset_data: dict) -> None:
        existing = self.get_company_assets(asset_key)
        payload = dict(asset_data)
        now = datetime.utcnow()
        payload.setdefault("asset_key", asset_key)
        payload.setdefault("updated_at", now)
        if not existing:
            payload.setdefault("created_at", now)
        self.update_one_doc("company_assets", {"asset_key": asset_key}, payload, upsert=True)

    def find_payment_gateway(self, gateway_id: str) -> dict | None:
        return self.find_one_doc("payment_gateways", {"gatewayId": gateway_id})

    def upsert_payment_gateway(self, gateway_id: str, updates: dict) -> None:
        existing = self.find_payment_gateway(gateway_id)
        payload = dict(updates)
        now = datetime.utcnow()
        payload.setdefault("gatewayId", gateway_id)
        payload.setdefault("updated_at", now)
        if not existing:
            payload.setdefault("created_at", now)
        self.update_one_doc("payment_gateways", {"gatewayId": gateway_id}, payload, upsert=True)

    def find_one(self, collection_name: str, filter_doc: dict) -> dict | None:
        return self.find_one_doc(collection_name, filter_doc)

    def insert_one(self, collection_name: str, doc: dict) -> dict:
        return self.insert_one_doc(collection_name, doc)

    def update_one(self, collection_name: str, filter_doc: dict, update_doc: dict, upsert: bool = False) -> int:
        return self.update_one_doc(collection_name, filter_doc, update_doc, upsert=upsert)

    def delete_many(self, collection_name: str, filter_doc: dict) -> int:
        return self.delete_many_docs(collection_name, filter_doc)

    def delete_users_except(self, keep_username: str) -> int:
        return self.delete_many_docs("users", {"username": {"$ne": keep_username}})

    def delete_user_role_mappings_except(self, keep_username: str) -> int:
        return self.delete_many_docs("user_role_mappings", {"username": {"$ne": keep_username}})

    def find_many(self, collection_name: str, filter_doc: dict, projection: dict | None = None) -> list[dict]:
        return self.find_many_docs(collection_name, filter_doc, projection=projection)

    def list_user_orders(self, customer_keys: list[str], skip: int = 0, limit: int = 10) -> list[dict]:
        if not customer_keys:
            return []
        return self.find_many_docs(
            "orders",
            {"customer_id": {"$in": customer_keys}},
            order_by="created_at",
            descending=True,
            skip=skip,
            limit=limit,
        )

    def find_order_by_id(self, order_id: str) -> dict | None:
        return self.find_one_doc("orders", {"id": order_id})

    def update_order(self, order_id: str, updates: dict) -> int:
        return self.update_one_doc("orders", {"id": order_id}, updates)

    def create_order(self, doc: dict) -> dict:
        return self.insert_one_doc("orders", doc)

    def increment_product_stock(self, product_id: str, qty_delta: int) -> None:
        self._execute(
            (
                "UPDATE products SET stock_quantity = stock_quantity + %s, updated_at = %s "
                "WHERE id = %s"
            ),
            [int(qty_delta), datetime.utcnow(), product_id],
        )

    def distinct_cart_session_ids(self) -> list[str]:
        rows = self._execute("SELECT DISTINCT session_id FROM cart_items", fetchall=True) or []
        return [row.get("session_id") for row in rows if row.get("session_id")]

    def list_cart_items_by_session(self, session_id: str) -> list[dict]:
        return self.find_many_docs("cart", {"session_id": session_id})

    def delete_checkout_locks_by_quote_ids(self, quote_ids: list[str]) -> int:
        if not quote_ids:
            return 0
        placeholders = ", ".join(["%s"] * len(quote_ids))
        return self._execute(
            f"DELETE FROM checkout_locks WHERE cart_quote_id IN ({placeholders})",
            quote_ids,
        )

    def delete_cart_items_by_session(self, session_id: str) -> int:
        return self.delete_many_docs("cart", {"session_id": session_id})