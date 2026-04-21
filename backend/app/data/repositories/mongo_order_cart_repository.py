"""MongoDB-backed cart/order gateway repository."""
from contextlib import contextmanager
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.database import get_collection
from app.domain.contracts.order_cart_repository import OrderCartRepository


class MongoOrderCartRepository(OrderCartRepository):
    """Mongo implementation for cart/order persistence gateway."""

    _checkout_index_ensured = False

    @contextmanager
    def transaction(self):
        yield

    def collection(self, name: str):
        return get_collection(name)

    def users_collection(self):
        return get_collection("users")

    def products_collection(self):
        return get_collection("products")

    def cart_collection(self):
        return get_collection("cart")

    def categories_collection(self):
        return get_collection("categories")

    def orders_collection(self):
        return get_collection("orders")

    def ledger_collection(self):
        return get_collection("ledger")

    def stock_ledger_collection(self):
        return get_collection("stock_ledger")

    def payments_collection(self):
        return get_collection("payments")

    def checkout_locks_collection(self):
        return get_collection("checkout_locks")

    def vendors_collection(self):
        return get_collection("vendors")

    def saved_products_collection(self):
        return get_collection("saved_products")

    def contact_inquiries_collection(self):
        return get_collection("contact_inquiries")

    def company_assets_collection(self):
        return get_collection("company_assets")

    def company_config_collection(self):
        return get_collection("company_config")

    def payment_gateways_collection(self):
        return get_collection("payment_gateways")

    def find_user_by_username(self, username: str) -> dict | None:
        return self.users_collection().find_one({"username": username})

    def find_product_by_id(self, product_id: str) -> dict | None:
        try:
            product_oid = ObjectId(product_id)
        except Exception:
            return None
        return self.products_collection().find_one({"_id": product_oid})

    def find_cart_item(self, user_id: str, session_id: str, product_id: str) -> dict | None:
        return self.cart_collection().find_one({
            "user_id": user_id,
            "session_id": session_id,
            "product_id": product_id,
        })

    def find_any_cart_item(self, user_id: str, session_id: str) -> dict | None:
        return self.cart_collection().find_one({"user_id": user_id, "session_id": session_id})

    def update_cart_item_quantity(self, cart_item_id, quantity_delta: int) -> None:
        self.cart_collection().update_one(
            {"_id": cart_item_id},
            {"$inc": {"quantity": quantity_delta}, "$set": {"updated_at": datetime.utcnow()}},
        )

    def backfill_cart_quote_id(self, user_id: str, session_id: str, cart_quote_id: str) -> None:
        self.cart_collection().update_many(
            {"user_id": user_id, "session_id": session_id, "cart_quote_id": {"$exists": False}},
            {"$set": {"cart_quote_id": cart_quote_id}},
        )

    def insert_cart_item(self, doc: dict) -> None:
        self.cart_collection().insert_one(doc)

    def list_cart_items(self, user_id: str, session_id: str) -> list[dict]:
        return list(self.cart_collection().find({"user_id": user_id, "session_id": session_id}))

    def remove_cart_item(self, user_id: str, session_id: str, product_id: str) -> int:
        result = self.cart_collection().delete_one(
            {"user_id": user_id, "session_id": session_id, "product_id": product_id}
        )
        return int(result.deleted_count)

    def clear_session_cart(self, user_id: str, session_id: str) -> None:
        self.cart_collection().delete_many({"user_id": user_id, "session_id": session_id})

    def acquire_checkout_lock(self, cart_quote_id: str, session_id: str, ttl_minutes: int) -> None:
        locks_col = self.checkout_locks_collection()
        now = datetime.utcnow()
        expiry = now + timedelta(minutes=ttl_minutes)

        if not MongoOrderCartRepository._checkout_index_ensured:
            locks_col.create_index("cart_quote_id", unique=True)
            MongoOrderCartRepository._checkout_index_ensured = True

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
        except DuplicateKeyError as error:
            raise ValueError("checkout_lock_conflict") from error

    def release_checkout_lock(self, cart_quote_id: str) -> None:
        self.checkout_locks_collection().delete_one({"cart_quote_id": cart_quote_id})

    def set_customer_business_id(self, user_id, customer_id: str) -> None:
        self.users_collection().update_one(
            {"_id": user_id},
            {"$set": {"customer_id": customer_id, "updated_at": datetime.utcnow()}},
        )

    def insert_payment_record(self, doc: dict) -> None:
        self.payments_collection().insert_one(doc)

    def find_pending_razorpay_payment(self, razorpay_order_id: str, username: str) -> dict | None:
        return self.payments_collection().find_one(
            {
                "provider": "razorpay",
                "status": "created",
                "razorpay_order_id": razorpay_order_id,
                "username": username,
            }
        )

    def mark_payment_verified(self, payment_id, razorpay_payment_id: str, razorpay_signature: str) -> None:
        self.payments_collection().update_one(
            {"_id": payment_id},
            {
                "$set": {
                    "status": "verified",
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    def decrement_product_stock_if_available(self, product_id: str, quantity: int) -> bool:
        try:
            product_oid = ObjectId(product_id)
        except Exception:
            return False
        result = self.products_collection().update_one(
            {"_id": product_oid, "stock_quantity": {"$gte": quantity}},
            {"$inc": {"stock_quantity": -quantity}, "$set": {"updated_at": datetime.utcnow()}},
        )
        return result.matched_count > 0

    def insert_stock_ledger_row(self, doc: dict) -> None:
        self.stock_ledger_collection().insert_one(doc)

    def insert_order(self, doc: dict):
        result = self.orders_collection().insert_one(doc)
        return result.inserted_id

    def update_user_address_data_if_changed(self, user_id, current_address: dict, new_address: dict) -> None:
        if new_address != (current_address or {}):
            self.users_collection().update_one(
                {"_id": user_id},
                {"$set": {"address_data": new_address, "updated_at": datetime.utcnow()}},
            )

    def insert_sales_ledger_row(self, doc: dict) -> None:
        self.ledger_collection().insert_one(doc)

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Categories
    # ------------------------------------------------------------------

    def _fmt(self, doc: dict) -> dict:
        doc["id"] = str(doc.pop("_id"))
        return doc

    def list_categories(self, skip: int = 0, limit: int = 50) -> list[dict]:
        docs = list(self.categories_collection().find().skip(skip).limit(limit))
        return [self._fmt(d) for d in docs]

    def find_category_by_name(self, name: str) -> dict | None:
        return self.categories_collection().find_one({"name": name})

    def create_category(self, doc: dict) -> dict:
        res = self.categories_collection().insert_one(doc)
        doc["_id"] = res.inserted_id
        return self._fmt(doc)

    def get_category(self, cat_id: str) -> dict | None:
        try:
            oid = ObjectId(cat_id)
        except Exception:
            return None
        doc = self.categories_collection().find_one({"_id": oid})
        if doc:
            return self._fmt(doc)
        return None

    def update_category(self, cat_id: str, updates: dict) -> int:
        try:
            oid = ObjectId(cat_id)
        except Exception:
            return 0
        res = self.categories_collection().update_one({"_id": oid}, {"$set": updates})
        return int(res.matched_count)

    def delete_category(self, cat_id: str) -> int:
        try:
            oid = ObjectId(cat_id)
        except Exception:
            return 0
        res = self.categories_collection().delete_one({"_id": oid})
        return int(res.deleted_count)

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Vendors
    # ------------------------------------------------------------------

    def list_vendors(self, skip: int = 0, limit: int = 50) -> list[dict]:
        docs = list(self.vendors_collection().find().skip(skip).limit(limit))
        return [self._fmt(d) for d in docs]

    def find_vendor_by_email(self, email: str) -> dict | None:
        return self.vendors_collection().find_one({"email": email})

    def create_vendor(self, doc: dict) -> dict:
        res = self.vendors_collection().insert_one(doc)
        doc["_id"] = res.inserted_id
        return self._fmt(doc)

    def get_vendor(self, vendor_id: str) -> dict | None:
        try:
            oid = ObjectId(vendor_id)
        except Exception:
            return None
        doc = self.vendors_collection().find_one({"_id": oid})
        if doc:
            return self._fmt(doc)
        return None

    def update_vendor(self, vendor_id: str, updates: dict) -> int:
        try:
            oid = ObjectId(vendor_id)
        except Exception:
            return 0
        res = self.vendors_collection().update_one({"_id": oid}, {"$set": updates})
        return int(res.matched_count)

    def delete_vendor(self, vendor_id: str) -> int:
        try:
            oid = ObjectId(vendor_id)
        except Exception:
            return 0
        res = self.vendors_collection().delete_one({"_id": oid})
        return int(res.deleted_count)

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Contact Inquiries
    # ------------------------------------------------------------------

    def create_contact_inquiry(self, doc: dict) -> dict:
        res = self.contact_inquiries_collection().insert_one(doc)
        doc["_id"] = res.inserted_id
        return self._fmt(doc)

    def list_contact_inquiries(
        self, skip: int = 0, limit: int = 50, status_filter: str | None = None
    ) -> list[dict]:
        query = {"status": status_filter} if status_filter else {}
        docs = list(
            self.contact_inquiries_collection()
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [self._fmt(d) for d in docs]

    def get_contact_inquiry(self, inquiry_id: str) -> dict | None:
        try:
            oid = ObjectId(inquiry_id)
        except Exception:
            return None
        doc = self.contact_inquiries_collection().find_one({"_id": oid})
        if doc:
            return self._fmt(doc)
        return None

    def update_contact_inquiry(self, inquiry_id: str, updates: dict) -> int:
        try:
            oid = ObjectId(inquiry_id)
        except Exception:
            return 0
        res = self.contact_inquiries_collection().update_one({"_id": oid}, {"$set": updates})
        return int(res.matched_count)

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Stock Ledger
    # ------------------------------------------------------------------

    def list_stock_ledger(
        self,
        product_id_filter: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        query = {"product_id": product_id_filter} if product_id_filter else {}
        docs = list(
            self.stock_ledger_collection()
            .find(query)
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [self._fmt(d) for d in docs]

    def add_stock_entry(self, entry_doc: dict) -> dict:
        res = self.stock_ledger_collection().insert_one(entry_doc)
        entry_doc["_id"] = res.inserted_id
        return self._fmt(entry_doc)

    def get_stock_entry(self, entry_id: str) -> dict | None:
        try:
            oid = ObjectId(entry_id)
        except Exception:
            return None
        doc = self.stock_ledger_collection().find_one({"_id": oid})
        if doc:
            return self._fmt(doc)
        return None

    def update_product_stock(self, product_id: str, new_qty: int) -> None:
        try:
            oid = ObjectId(product_id)
        except Exception:
            return
        self.products_collection().update_one(
            {"_id": oid},
            {"$set": {"stock_quantity": new_qty, "updated_at": datetime.utcnow()}},
        )

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Saved Products
    # ------------------------------------------------------------------

    def find_saved_product(self, user_id: str, product_id: str) -> dict | None:
        return self.saved_products_collection().find_one(
            {"customer_id": user_id, "product_id": product_id}
        )

    def create_saved_product(self, doc: dict) -> dict:
        res = self.saved_products_collection().insert_one(doc)
        doc["_id"] = res.inserted_id
        return doc

    def list_saved_products_for_user(self, user_id: str) -> list[dict]:
        return list(self.saved_products_collection().find({"customer_id": user_id}))

    def delete_saved_product(self, user_id: str, product_id: str) -> int:
        res = self.saved_products_collection().delete_one(
            {"customer_id": user_id, "product_id": product_id}
        )
        return int(res.deleted_count)

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Orders (admin)
    # ------------------------------------------------------------------

    def list_orders_filtered(self, query: dict, skip: int = 0, limit: int = 50) -> list[dict]:
        docs = list(
            self.orders_collection().find(query).sort("created_at", -1).skip(skip).limit(limit)
        )
        for d in docs:
            d["id"] = str(d.pop("_id"))
        return docs

    def aggregate_orders(self, pipeline: list) -> list[dict]:
        return list(self.orders_collection().aggregate(pipeline))

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
        pipeline = [{"$addFields": {"id": {"$toString": "$_id"}}}]
        match_query: dict = {}

        if date_from or date_to:
            created_range: dict = {}
            if date_from:
                created_range["$gte"] = date_from
            if date_to:
                created_range["$lte"] = date_to
            match_query["created_at"] = created_range

        if amount_min is not None or amount_max is not None:
            amount_range: dict = {}
            if amount_min is not None:
                amount_range["$gte"] = amount_min
            if amount_max is not None:
                amount_range["$lte"] = amount_max
            match_query["total"] = amount_range

        if order_id:
            pipeline.append({
                "$match": {
                    "$or": [
                        {"id": {"$regex": order_id, "$options": "i"}},
                        {"order_number": {"$regex": order_id, "$options": "i"}},
                    ]
                }
            })

        if order_number:
            pipeline.append({
                "$match": {"order_number": {"$regex": order_number, "$options": "i"}}
            })

        if match_query:
            pipeline.append({"$match": match_query})

        total_pipeline = pipeline + [{"$count": "count"}]
        total_result = list(self.orders_collection().aggregate(total_pipeline))
        total = total_result[0]["count"] if total_result else 0

        result_pipeline = pipeline + [
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
        ]
        docs = list(self.orders_collection().aggregate(result_pipeline))
        for d in docs:
            d.pop("_id", None)

        return docs, total

    def update_order_status(self, order_id: str, new_status: str, updated_at=None) -> int:
        try:
            oid = ObjectId(order_id)
        except Exception:
            return 0
        ts = updated_at or datetime.utcnow()
        res = self.orders_collection().update_one(
            {"_id": oid},
            {"$set": {"status": new_status, "updated_at": ts}},
        )
        return int(res.matched_count)

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Company Config / Assets / Gateways
    # ------------------------------------------------------------------

    def find_company_config(self, config_id: str) -> dict | None:
        return self.company_config_collection().find_one({"configId": config_id})

    def upsert_company_config(self, config_id: str, updates: dict) -> None:
        self.company_config_collection().update_one(
            {"configId": config_id},
            {"$set": updates},
            upsert=True,
        )

    def get_company_assets(self, asset_key: str = "company_image") -> dict | None:
        return self.company_assets_collection().find_one({"asset_key": asset_key})

    def upsert_company_asset(self, asset_key: str, asset_data: dict) -> None:
        from bson.binary import Binary
        if "data" in asset_data and isinstance(asset_data["data"], (bytes, bytearray)):
            asset_data = {**asset_data, "data": Binary(asset_data["data"])}
        self.company_assets_collection().update_one(
            {"asset_key": asset_key},
            {"$set": asset_data, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )

    def find_payment_gateway(self, gateway_id: str) -> dict | None:
        return self.payment_gateways_collection().find_one({"gatewayId": gateway_id})

    def upsert_payment_gateway(self, gateway_id: str, updates: dict) -> None:
        self.payment_gateways_collection().update_one(
            {"gatewayId": gateway_id},
            {"$set": updates},
            upsert=True,
        )

    # ------------------------------------------------------------------
    # Phase 2/3: Named operations — Generic helpers for admin / data_sync
    # ------------------------------------------------------------------

    @staticmethod
    def _to_mongo_filter(filter_doc: dict) -> dict:
        """Convert abstract 'id' key to Mongo '_id' with ObjectId."""
        out = dict(filter_doc)
        if "id" in out:
            try:
                out["_id"] = ObjectId(out.pop("id"))
            except Exception:
                out["_id"] = out.pop("id")
        return out

    def find_one(self, collection_name: str, filter_doc: dict) -> dict | None:
        doc = get_collection(collection_name).find_one(self._to_mongo_filter(filter_doc))
        return self._fmt(doc) if doc else None

    def insert_one(self, collection_name: str, doc: dict) -> dict:
        res = get_collection(collection_name).insert_one(doc)
        doc["_id"] = res.inserted_id
        return self._fmt(doc)

    def update_one(
        self, collection_name: str, filter_doc: dict, update_doc: dict, upsert: bool = False
    ) -> int:
        res = get_collection(collection_name).update_one(
            self._to_mongo_filter(filter_doc), {"$set": update_doc}, upsert=upsert
        )
        return int(res.matched_count)

    def delete_many(self, collection_name: str, filter_doc: dict) -> int:
        res = get_collection(collection_name).delete_many(self._to_mongo_filter(filter_doc))
        return int(res.deleted_count)

    def delete_users_except(self, keep_username: str) -> int:
        res = self.users_collection().delete_many({"username": {"$ne": keep_username}})
        return int(res.deleted_count)

    def delete_user_role_mappings_except(self, keep_username: str) -> int:
        res = get_collection("user_role_mappings").delete_many({"username": {"$ne": keep_username}})
        return int(res.deleted_count)

    def find_many(
        self,
        collection_name: str,
        filter_doc: dict,
        projection: dict | None = None,
    ) -> list[dict]:
        kwargs: dict = {}
        if projection:
            kwargs["projection"] = projection
        return [self._fmt(d) for d in get_collection(collection_name).find(self._to_mongo_filter(filter_doc), **kwargs)]

    # ------------------------------------------------------------------
    # Phase 3: Named operations — Orders (customer-facing)
    # ------------------------------------------------------------------

    def list_user_orders(
        self, customer_keys: list[str], skip: int = 0, limit: int = 10
    ) -> list[dict]:
        docs = list(
            self.orders_collection()
            .find({"customer_id": {"$in": customer_keys}})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return docs

    def find_order_by_id(self, order_id: str) -> dict | None:
        try:
            oid = ObjectId(order_id)
        except Exception:
            return None
        return self.orders_collection().find_one({"_id": oid})

    def update_order(self, order_id: str, updates: dict) -> int:
        try:
            oid = ObjectId(order_id)
        except Exception:
            return 0
        res = self.orders_collection().update_one({"_id": oid}, {"$set": updates})
        return int(res.matched_count)

    def create_order(self, doc: dict) -> dict:
        res = self.orders_collection().insert_one(doc)
        doc["_id"] = res.inserted_id
        doc["id"] = str(res.inserted_id)
        return doc

    def increment_product_stock(self, product_id: str, qty_delta: int) -> None:
        try:
            oid = ObjectId(product_id)
        except Exception:
            return
        self.products_collection().update_one(
            {"_id": oid},
            {"$inc": {"stock_quantity": qty_delta}, "$set": {"updated_at": datetime.utcnow()}},
        )

    # ------------------------------------------------------------------
    # Phase 4: Cart cleanup operations
    # ------------------------------------------------------------------

    def distinct_cart_session_ids(self) -> list[str]:
        return self.cart_collection().distinct("session_id")

    def list_cart_items_by_session(self, session_id: str) -> list[dict]:
        return list(self.cart_collection().find({"session_id": session_id}))

    def delete_checkout_locks_by_quote_ids(self, quote_ids: list[str]) -> int:
        if not quote_ids:
            return 0
        result = self.checkout_locks_collection().delete_many(
            {"cart_quote_id": {"$in": quote_ids}}
        )
        return result.deleted_count

    def delete_cart_items_by_session(self, session_id: str) -> int:
        result = self.cart_collection().delete_many({"session_id": session_id})
        return result.deleted_count
