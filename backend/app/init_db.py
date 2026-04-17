"""Initialize and validate main database and log database at startup."""
from pymongo import MongoClient, ASCENDING, errors
from pymongo.collection import Collection
from app.config import settings
from app.utils.security import hash_password
from datetime import datetime, timedelta

MASTER_COLLECTIONS = [
    "users",
    "products",
    "categories",
    "customers",
    "vendors",
    "counters",
]
TRANSACTION_COLLECTIONS = [
    "orders",
    "order_items",
    "payments",
    "invoices",
    "carts",
    "contact_inquiries",
]
LEDGER_COLLECTIONS = [
    "stock_ledger",
    "financial_ledger",
    "sessions",
]
MAPPING_COLLECTIONS = [
    "role_permissions",
    "user_role_mappings",
    "role_functionality_mappings",
]
ASSET_COLLECTIONS = [
    "company_assets",
    "product_media",
]
LOG_COLLECTION = "audit_logs"


def _get_client() -> MongoClient:
    client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client


def _ensure_collections(db):
    existing = db.list_collection_names()
    all_collections = (
        MASTER_COLLECTIONS + TRANSACTION_COLLECTIONS
        + LEDGER_COLLECTIONS + MAPPING_COLLECTIONS + ASSET_COLLECTIONS
    )
    for name in all_collections:
        if name not in existing:
            db.create_collection(name)


def _ensure_indexes(db):
    """Create indexes for performance and constraints."""
    db["users"].create_index("username", unique=True, background=True)
    db["users"].create_index("email", unique=True, sparse=True, background=True)
    db["users"].create_index("customer_id", unique=True, sparse=True, background=True)
    db["products"].create_index("sku", unique=True, background=True)
    db["products"].create_index("barcode", background=True)
    db["products"].create_index("created_at", background=True)
    db["products"].create_index("name", background=True)
    db["products"].create_index("sell_price", background=True)
    db["categories"].create_index("name", unique=True, background=True)
    db["vendors"].create_index("email", unique=True, sparse=True, background=True)
    db["orders"].create_index([("customer_id", ASCENDING), ("created_at", ASCENDING)], background=True)
    db["orders"].create_index("order_number", sparse=True, background=True)
    db["sessions"].create_index("username", background=True)
    db["sessions"].create_index("expires_at", background=True)
    db["sessions"].create_index(
        [("username", ASCENDING), ("client_ip", ASCENDING), ("client_mac", ASCENDING)],
        background=True,
    )
    db["user_role_mappings"].create_index("username", unique=True, background=True)
    db["role_functionality_mappings"].create_index(
        [("role", ASCENDING), ("functionality_code", ASCENDING)],
        unique=True, background=True
    )
    db["company_assets"].create_index("asset_key", unique=True, background=True)
    db["product_media"].create_index([("product_id", ASCENDING), ("created_at", ASCENDING)], background=True)
    db["contact_inquiries"].create_index("created_at", background=True)
    db["ledger"].create_index("created_at", background=True)
    db["data_sync_jobs"].create_index("created_at", background=True)
    db["stock_ledger"].create_index("created_at", background=True)


def _create_admin_user(db):
    users: Collection = db["users"]
    existing_admin = users.find_one({"username": settings.admin_username})
    if existing_admin:
        users.update_one(
            {"_id": existing_admin["_id"]},
            {
                "$set": {
                    "email": settings.admin_email,
                    "password_hash": hash_password(settings.admin_password),
                    "role": "admin",
                    "full_name": existing_admin.get("full_name") or "Administrator",
                    "phone": existing_admin.get("phone", ""),
                    "address": existing_admin.get("address", ""),
                    "is_active": True,
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow(),
                },
            },
        )
        return True

    admin_entry = {
        "username": settings.admin_username,
        "email": settings.admin_email,
        "password_hash": hash_password(settings.admin_password),
        "role": "admin",
        "full_name": "Administrator",
        "phone": "",
        "address": "",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    users.insert_one(admin_entry)
    return True


def _ensure_logdb(client):
    if settings.log_database not in client.list_database_names():
        logdb = client[settings.log_database]
        logdb.create_collection(LOG_COLLECTION)
    else:
        logdb = client[settings.log_database]
        if LOG_COLLECTION not in logdb.list_collection_names():
            logdb.create_collection(LOG_COLLECTION)

    # We enforce insert-only for logs by application policy; no update/delete endpoints provided.
    logdb[LOG_COLLECTION].create_index("created_at", background=True)
    return logdb[LOG_COLLECTION]


def initialize_databases():
    client = None
    try:
        client = _get_client()
        appdb_name = settings.mongodb_database

        if appdb_name in client.list_database_names():
            appdb = client[appdb_name]
            user_exists = appdb["users"].find_one({"username": settings.admin_username})
            if not user_exists:
                # user missing -> drop and recreate
                client.drop_database(appdb_name)
                appdb = client[appdb_name]
        else:
            appdb = client[appdb_name]

        _ensure_collections(appdb)
        _ensure_indexes(appdb)
        if not _create_admin_user(appdb):
            raise RuntimeError("Could not create admin user")

        _ensure_logdb(client)

        return appdb
    except Exception as err:
        raise RuntimeError(f"Database initialization failed: {err}")
    finally:
        if client:
            client.close()
