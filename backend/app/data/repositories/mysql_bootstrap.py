"""MySQL-backed database bootstrap implementation."""
from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.data.mysql_client import mysql_server_connection
from app.data.mysql_support import MYSQL_TABLE_SPECS
from app.data.repositories.mysql_utility_repository import MySQLUtilityRepository
from app.domain.contracts.database_bootstrap import DatabaseBootstrap
from app.utils.security import hash_password


class MySQLBootstrap(DatabaseBootstrap):
    """Create the MySQL schema, indexes, and baseline admin account."""

    # Additional columns that store datetime values but don't follow the '_at' suffix convention.
    _EXTRA_DATETIME_COLUMNS = {
        "last_activity",
        "started_at",
        "finished_at",
        "verified_at",
        "used_at",
    }

    _LONGTEXT_COLUMNS = {
        "description",
        "address",
        "message",
        "notes",
        "bank_details",
        "subject",
    }
    _TEXT_COLUMNS = {
        "full_name",
        "email",
        "password_hash",
        "phone",
        "dob",
        "sex",
        "marital_status",
        "category",
        "filename",
        "content_type",
        "media_type",
        "product_name",
        "reference",
        "transaction_type",
        "payment_method",
        "payment_status",
        "payment_provider",
        "payment_reference",
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        "currency",
        "receipt",
        "status",
        "configId",
        "gatewayId",
        "asset_key",
        "functionality_code",
        "role",
        "username",
        "token",
        "client_ip",
        "client_mac",
        "customer_id",
        "order_number",
        "cart_quote_id",
        "product_id",
        "sku",
        "barcode",
        "name",
        "discount",
        "discount_type",
        "provider",
        "authkey",
        "template_id",
        "sender_id",
        "counter_key",
        "action",
        "user",
        "path",
        "created_by",
        "updated_by",
        "purpose",
        "otp",
        "gatewayId",
        "configId",
        "extension",
        "email",
        "state",
        "country",
        "district",
        "area",
        "street1",
        "street2",
        "landmark",
        "pincode",
    }
    _INT_COLUMNS = {
        "quantity",
        "stock_quantity",
        "processed_rows",
        "success_rows",
        "failed_rows",
        "verification_attempts",
        "size",
        "amount",
    }
    _INDEX_DEFINITIONS = {
        "users": [
            ("idx_users_username", "CREATE UNIQUE INDEX idx_users_username ON users (username)"),
            ("idx_users_email", "CREATE UNIQUE INDEX idx_users_email ON users (email)"),
            ("idx_users_customer_id", "CREATE UNIQUE INDEX idx_users_customer_id ON users (customer_id)"),
        ],
        "products": [
            ("idx_products_sku", "CREATE UNIQUE INDEX idx_products_sku ON products (sku)"),
            ("idx_products_barcode", "CREATE INDEX idx_products_barcode ON products (barcode)"),
            ("idx_products_created_at", "CREATE INDEX idx_products_created_at ON products (created_at)"),
            ("idx_products_name", "CREATE INDEX idx_products_name ON products (name)"),
            ("idx_products_sell_price", "CREATE INDEX idx_products_sell_price ON products (sell_price)"),
        ],
        "categories": [
            ("idx_categories_name", "CREATE UNIQUE INDEX idx_categories_name ON categories (name)"),
        ],
        "vendors": [
            ("idx_vendors_email", "CREATE UNIQUE INDEX idx_vendors_email ON vendors (email)"),
        ],
        "orders": [
            ("idx_orders_customer_created", "CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at)"),
            ("idx_orders_order_number", "CREATE INDEX idx_orders_order_number ON orders (order_number)"),
        ],
        "sessions": [
            ("idx_sessions_username", "CREATE INDEX idx_sessions_username ON sessions (username)"),
            ("idx_sessions_expires_at", "CREATE INDEX idx_sessions_expires_at ON sessions (expires_at)"),
            ("idx_sessions_identity", "CREATE INDEX idx_sessions_identity ON sessions (username, client_ip, client_mac)"),
        ],
        "user_role_mappings": [
            ("idx_user_role_mappings_username", "CREATE UNIQUE INDEX idx_user_role_mappings_username ON user_role_mappings (username)"),
        ],
        "role_functionality_mappings": [
            (
                "idx_role_functionality_unique",
                "CREATE UNIQUE INDEX idx_role_functionality_unique ON role_functionality_mappings (role, functionality_code)",
            ),
        ],
        "company_assets": [
            ("idx_company_assets_asset_key", "CREATE UNIQUE INDEX idx_company_assets_asset_key ON company_assets (asset_key)"),
        ],
        "product_media": [
            ("idx_product_media_product_created", "CREATE INDEX idx_product_media_product_created ON product_media (product_id, created_at)"),
        ],
        "contact_inquiries": [
            ("idx_contact_inquiries_created_at", "CREATE INDEX idx_contact_inquiries_created_at ON contact_inquiries (created_at)"),
        ],
        "ledger_entries": [
            ("idx_ledger_entries_created_at", "CREATE INDEX idx_ledger_entries_created_at ON ledger_entries (created_at)"),
        ],
        "data_sync_jobs": [
            ("idx_data_sync_jobs_created_at", "CREATE INDEX idx_data_sync_jobs_created_at ON data_sync_jobs (created_at)"),
        ],
        "stock_ledger": [
            ("idx_stock_ledger_created_at", "CREATE INDEX idx_stock_ledger_created_at ON stock_ledger (created_at)"),
        ],
        "checkout_locks": [
            ("idx_checkout_locks_cart_quote_id", "CREATE UNIQUE INDEX idx_checkout_locks_cart_quote_id ON checkout_locks (cart_quote_id)"),
        ],
    }

    def _column_definition(self, spec_name: str, column: str) -> str:
        spec = MYSQL_TABLE_SPECS[spec_name]
        if column in spec.binary_columns:
            return f"`{column}` LONGBLOB NULL"
        if column in spec.bool_columns:
            return f"`{column}` TINYINT(1) NOT NULL DEFAULT 0"
        if column in spec.decimal_columns:
            scale = "4" if column == "gst_rate" else "2"
            return f"`{column}` DECIMAL(12,{scale}) NULL"
        if column.endswith("_at") or column in self._EXTRA_DATETIME_COLUMNS:
            return f"`{column}` DATETIME NULL"
        if column in self._INT_COLUMNS:
            return f"`{column}` INT NULL"
        if column in self._LONGTEXT_COLUMNS:
            return f"`{column}` LONGTEXT NULL"
        if column == spec.id_column:
            return f"`{column}` VARCHAR(191) NOT NULL"
        if column in self._TEXT_COLUMNS:
            return f"`{column}` VARCHAR(255) NULL"
        return f"`{column}` LONGTEXT NULL"

    def _create_table_sql(self, spec_name: str) -> str:
        spec = MYSQL_TABLE_SPECS[spec_name]
        column_defs = [self._column_definition(spec_name, column) for column in spec.columns]
        if spec.json_column:
            column_defs.append(f"`{spec.json_column}` LONGTEXT NULL")
        column_defs.append(f"PRIMARY KEY (`{spec.id_column}`)")
        return (
            f"CREATE TABLE IF NOT EXISTS `{spec.table_name}` ("
            + ", ".join(column_defs)
            + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )

    def _ensure_database(self, database_name: str) -> None:
        with mysql_server_connection(database=None) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )

    def _ensure_tables(self) -> None:
        main_specs = [name for name in MYSQL_TABLE_SPECS if name != "audit_logs"]
        with mysql_server_connection(database=settings.mysql_database) as connection:
            with connection.cursor() as cursor:
                for spec_name in main_specs:
                    cursor.execute(self._create_table_sql(spec_name))

        with mysql_server_connection(database=settings.log_database) as connection:
            with connection.cursor() as cursor:
                cursor.execute(self._create_table_sql("audit_logs"))

    def _ensure_indexes(self) -> None:
        with mysql_server_connection(database=settings.mysql_database) as connection:
            with connection.cursor() as cursor:
                for table_name, index_defs in self._INDEX_DEFINITIONS.items():
                    for index_name, ddl in index_defs:
                        cursor.execute(f"SHOW INDEX FROM `{table_name}` WHERE Key_name = %s", [index_name])
                        if cursor.fetchone():
                            continue
                        cursor.execute(ddl)

        with mysql_server_connection(database=settings.log_database) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SHOW INDEX FROM `audit_logs` WHERE Key_name = %s", ["idx_audit_logs_created_at"])
                if not cursor.fetchone():
                    cursor.execute("CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at)")

    def _ensure_admin_user(self) -> None:
        repo = MySQLUtilityRepository()
        existing = repo.find_user({"username": settings.admin_username})
        admin_updates = {
            "email": settings.admin_email,
            "password_hash": hash_password(settings.admin_password),
            "role": "admin",
            "full_name": (existing or {}).get("full_name") or "Administrator",
            "phone": (existing or {}).get("phone", ""),
            "address": (existing or {}).get("address", ""),
            "is_active": True,
            "updated_at": datetime.utcnow(),
        }
        if existing:
            repo.update_user({"username": settings.admin_username}, admin_updates)
            return
        repo.create_user_admin(
            {
                "username": settings.admin_username,
                "email": settings.admin_email,
                "password_hash": admin_updates["password_hash"],
                "role": "admin",
                "full_name": "Administrator",
                "phone": "",
                "address": "",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    def bootstrap(self) -> None:
        self._ensure_database(settings.mysql_database)
        self._ensure_database(settings.log_database)
        self._ensure_tables()
        self._ensure_indexes()
        self._ensure_admin_user()