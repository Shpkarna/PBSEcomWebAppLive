-- Phase 7 SQL Server application schema.
--
-- Default database names match backend/app/config.py defaults:
--   mssql_database    = ecomdb
-- Run against SQL Server 2017+ (or Express edition on localhost\SQLEXPRESS).
--
-- Usage:
--   sqlcmd -S localhost\SQLEXPRESS -E -i 001_phase7_app_schema.sql

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = N'ecomdb')
    EXEC('CREATE DATABASE [ecomdb] COLLATE Latin1_General_CI_AS');
GO

USE [ecomdb];
GO

-- --------------------------------------------------------------------------
-- users
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'users' AND type = N'U')
CREATE TABLE [users] (
    [id]                NVARCHAR(191) NOT NULL,
    [username]          NVARCHAR(255) NULL,
    [email]             NVARCHAR(255) NULL,
    [password_hash]     NVARCHAR(255) NULL,
    [full_name]         NVARCHAR(255) NULL,
    [phone]             NVARCHAR(255) NULL,
    [dob]               NVARCHAR(255) NULL,
    [sex]               NVARCHAR(255) NULL,
    [marital_status]    NVARCHAR(255) NULL,
    [address]           NVARCHAR(MAX) NULL,
    [role]              NVARCHAR(255) NULL,
    [customer_id]       NVARCHAR(255) NULL,
    [is_active]         BIT NOT NULL DEFAULT 0,
    [phone_verified]    BIT NOT NULL DEFAULT 0,
    [email_verified]    BIT NOT NULL DEFAULT 0,
    [created_at]        DATETIME2(0) NULL,
    [updated_at]        DATETIME2(0) NULL,
    [payload_json]      NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_users_username') CREATE UNIQUE INDEX idx_users_username ON users (username);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_users_email') CREATE UNIQUE INDEX idx_users_email ON users (email);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_users_customer_id') CREATE UNIQUE INDEX idx_users_customer_id ON users (customer_id) WHERE customer_id IS NOT NULL;
GO

-- --------------------------------------------------------------------------
-- sessions
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'sessions' AND type = N'U')
CREATE TABLE [sessions] (
    [id]                NVARCHAR(191) NOT NULL,
    [username]          NVARCHAR(255) NULL,
    [client_ip]         NVARCHAR(255) NULL,
    [client_mac]        NVARCHAR(255) NULL,
    [access_token]      NVARCHAR(MAX) NULL,
    [token_expires_at]  DATETIME2(0) NULL,
    [created_at]        DATETIME2(0) NULL,
    [expires_at]        DATETIME2(0) NULL,
    [last_activity]     DATETIME2(0) NULL,
    [payload_json]      NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_sessions_username') CREATE INDEX idx_sessions_username ON sessions (username);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_sessions_expires_at') CREATE INDEX idx_sessions_expires_at ON sessions (expires_at);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_sessions_identity') CREATE INDEX idx_sessions_identity ON sessions (username, client_ip, client_mac);
GO

-- --------------------------------------------------------------------------
-- email_verifications
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'email_verifications' AND type = N'U')
CREATE TABLE [email_verifications] (
    [id]            NVARCHAR(191) NOT NULL,
    [username]      NVARCHAR(255) NULL,
    [token]         NVARCHAR(255) NULL,
    [verified]      BIT NOT NULL DEFAULT 0,
    [verified_at]   DATETIME2(0) NULL,
    [expires_at]    DATETIME2(0) NULL,
    [created_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO

-- --------------------------------------------------------------------------
-- otp_records
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'otp_records' AND type = N'U')
CREATE TABLE [otp_records] (
    [id]                    NVARCHAR(191) NOT NULL,
    [phone]                 NVARCHAR(255) NULL,
    [purpose]               NVARCHAR(255) NULL,
    [otp]                   NVARCHAR(255) NULL,
    [created_at]            DATETIME2(0) NULL,
    [expires_at]            DATETIME2(0) NULL,
    [verified]              BIT NOT NULL DEFAULT 0,
    [verified_at]           DATETIME2(0) NULL,
    [used]                  BIT NOT NULL DEFAULT 0,
    [used_at]               DATETIME2(0) NULL,
    [verification_attempts] INT NULL,
    [payload_json]          NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO

-- --------------------------------------------------------------------------
-- products
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'products' AND type = N'U')
CREATE TABLE [products] (
    [id]                NVARCHAR(191) NOT NULL,
    [sku]               NVARCHAR(255) NULL,
    [name]              NVARCHAR(255) NULL,
    [barcode]           NVARCHAR(255) NULL,
    [description]       NVARCHAR(MAX) NULL,
    [category]          NVARCHAR(255) NULL,
    [stock_price]       DECIMAL(12,2) NULL,
    [sell_price]        DECIMAL(12,2) NULL,
    [discount]          NVARCHAR(255) NULL,
    [discount_value]    DECIMAL(12,2) NULL,
    [discount_type]     NVARCHAR(255) NULL,
    [stock_quantity]    INT NULL,
    [gst_rate]          DECIMAL(12,4) NULL,
    [is_active]         BIT NOT NULL DEFAULT 0,
    [created_at]        DATETIME2(0) NULL,
    [updated_at]        DATETIME2(0) NULL,
    [payload_json]      NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_products_sku') CREATE UNIQUE INDEX idx_products_sku ON products (sku);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_products_barcode') CREATE INDEX idx_products_barcode ON products (barcode);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_products_created_at') CREATE INDEX idx_products_created_at ON products (created_at);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_products_name') CREATE INDEX idx_products_name ON products (name);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_products_sell_price') CREATE INDEX idx_products_sell_price ON products (sell_price);
GO

-- --------------------------------------------------------------------------
-- product_media
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'product_media' AND type = N'U')
CREATE TABLE [product_media] (
    [id]            NVARCHAR(191) NOT NULL,
    [product_id]    NVARCHAR(255) NULL,
    [filename]      NVARCHAR(255) NULL,
    [content_type]  NVARCHAR(255) NULL,
    [media_type]    NVARCHAR(255) NULL,
    [size]          INT NULL,
    [created_at]    DATETIME2(0) NULL,
    [created_by]    NVARCHAR(255) NULL,
    [data]          VARBINARY(MAX) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_product_media_product_created') CREATE INDEX idx_product_media_product_created ON product_media (product_id, created_at);
GO

-- --------------------------------------------------------------------------
-- cart_items  (Python collection name: "cart")
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'cart_items' AND type = N'U')
CREATE TABLE [cart_items] (
    [id]            NVARCHAR(191) NOT NULL,
    [user_id]       NVARCHAR(MAX) NULL,
    [session_id]    NVARCHAR(MAX) NULL,
    [product_id]    NVARCHAR(255) NULL,
    [product_name]  NVARCHAR(255) NULL,
    [quantity]      INT NULL,
    [price]         DECIMAL(12,2) NULL,
    [gst_rate]      DECIMAL(12,4) NULL,
    [cart_quote_id] NVARCHAR(255) NULL,
    [created_at]    DATETIME2(0) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO

-- --------------------------------------------------------------------------
-- categories
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'categories' AND type = N'U')
CREATE TABLE [categories] (
    [id]                NVARCHAR(191) NOT NULL,
    [name]              NVARCHAR(255) NULL,
    [description]       NVARCHAR(MAX) NULL,
    [discount_type]     NVARCHAR(255) NULL,
    [discount_value]    DECIMAL(12,2) NULL,
    [created_at]        DATETIME2(0) NULL,
    [updated_at]        DATETIME2(0) NULL,
    [payload_json]      NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_categories_name') CREATE UNIQUE INDEX idx_categories_name ON categories (name);
GO

-- --------------------------------------------------------------------------
-- orders
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'orders' AND type = N'U')
CREATE TABLE [orders] (
    [id]                    NVARCHAR(191) NOT NULL,
    [customer_id]           NVARCHAR(255) NULL,
    [order_number]          NVARCHAR(255) NULL,
    [cart_quote_id]         NVARCHAR(255) NULL,
    [subtotal]              DECIMAL(12,2) NULL,
    [total_discount]        DECIMAL(12,2) NULL,
    [total_gst]             DECIMAL(12,2) NULL,
    [total]                 DECIMAL(12,2) NULL,
    [payment_method]        NVARCHAR(255) NULL,
    [payment_status]        NVARCHAR(255) NULL,
    [payment_provider]      NVARCHAR(255) NULL,
    [payment_reference]     NVARCHAR(255) NULL,
    [razorpay_order_id]     NVARCHAR(255) NULL,
    [status]                NVARCHAR(255) NULL,
    [created_at]            DATETIME2(0) NULL,
    [updated_at]            DATETIME2(0) NULL,
    [payload_json]          NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_orders_customer_created') CREATE INDEX idx_orders_customer_created ON orders (customer_id, created_at);
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_orders_order_number') CREATE INDEX idx_orders_order_number ON orders (order_number);
GO

-- --------------------------------------------------------------------------
-- ledger_entries  (Python collection name: "ledger")
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'ledger_entries' AND type = N'U')
CREATE TABLE [ledger_entries] (
    [id]                NVARCHAR(191) NOT NULL,
    [transaction_type]  NVARCHAR(255) NULL,
    [category]          NVARCHAR(255) NULL,
    [amount]            DECIMAL(12,2) NULL,
    [reference_id]      NVARCHAR(MAX) NULL,
    [notes]             NVARCHAR(MAX) NULL,
    [created_at]        DATETIME2(0) NULL,
    [payload_json]      NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_ledger_entries_created_at') CREATE INDEX idx_ledger_entries_created_at ON ledger_entries (created_at);
GO

-- --------------------------------------------------------------------------
-- stock_ledger
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'stock_ledger' AND type = N'U')
CREATE TABLE [stock_ledger] (
    [id]                NVARCHAR(191) NOT NULL,
    [product_id]        NVARCHAR(255) NULL,
    [transaction_type]  NVARCHAR(255) NULL,
    [quantity]          INT NULL,
    [reference]         NVARCHAR(255) NULL,
    [notes]             NVARCHAR(MAX) NULL,
    [created_at]        DATETIME2(0) NULL,
    [payload_json]      NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_stock_ledger_created_at') CREATE INDEX idx_stock_ledger_created_at ON stock_ledger (created_at);
GO

-- --------------------------------------------------------------------------
-- payments
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'payments' AND type = N'U')
CREATE TABLE [payments] (
    [id]                    NVARCHAR(191) NOT NULL,
    [provider]              NVARCHAR(255) NULL,
    [status]                NVARCHAR(255) NULL,
    [username]              NVARCHAR(255) NULL,
    [customer_id]           NVARCHAR(255) NULL,
    [payment_method]        NVARCHAR(255) NULL,
    [razorpay_order_id]     NVARCHAR(255) NULL,
    [razorpay_payment_id]   NVARCHAR(255) NULL,
    [razorpay_signature]    NVARCHAR(255) NULL,
    [amount]                INT NULL,
    [currency]              NVARCHAR(255) NULL,
    [receipt]               NVARCHAR(255) NULL,
    [created_at]            DATETIME2(0) NULL,
    [updated_at]            DATETIME2(0) NULL,
    [payload_json]          NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO

-- --------------------------------------------------------------------------
-- checkout_locks
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'checkout_locks' AND type = N'U')
CREATE TABLE [checkout_locks] (
    [cart_quote_id] NVARCHAR(191) NOT NULL,
    [session_id]    NVARCHAR(MAX) NULL,
    [expires_at]    DATETIME2(0) NULL,
    [created_at]    DATETIME2(0) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([cart_quote_id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_checkout_locks_cart_quote_id') CREATE UNIQUE INDEX idx_checkout_locks_cart_quote_id ON checkout_locks (cart_quote_id);
GO

-- --------------------------------------------------------------------------
-- vendors
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'vendors' AND type = N'U')
CREATE TABLE [vendors] (
    [id]            NVARCHAR(191) NOT NULL,
    [name]          NVARCHAR(255) NULL,
    [email]         NVARCHAR(255) NULL,
    [phone]         NVARCHAR(255) NULL,
    [address]       NVARCHAR(MAX) NULL,
    [gst_number]    NVARCHAR(MAX) NULL,
    [bank_details]  NVARCHAR(MAX) NULL,
    [created_at]    DATETIME2(0) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_vendors_email') CREATE UNIQUE INDEX idx_vendors_email ON vendors (email);
GO

-- --------------------------------------------------------------------------
-- saved_products
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'saved_products' AND type = N'U')
CREATE TABLE [saved_products] (
    [id]            NVARCHAR(191) NOT NULL,
    [customer_id]   NVARCHAR(255) NULL,
    [product_id]    NVARCHAR(255) NULL,
    [saved_price]   DECIMAL(12,2) NULL,
    [created_at]    DATETIME2(0) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO

-- --------------------------------------------------------------------------
-- contact_inquiries
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'contact_inquiries' AND type = N'U')
CREATE TABLE [contact_inquiries] (
    [id]            NVARCHAR(191) NOT NULL,
    [name]          NVARCHAR(255) NULL,
    [email]         NVARCHAR(255) NULL,
    [phone]         NVARCHAR(255) NULL,
    [subject]       NVARCHAR(MAX) NULL,
    [message]       NVARCHAR(MAX) NULL,
    [status]        NVARCHAR(255) NULL,
    [created_at]    DATETIME2(0) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_contact_inquiries_created_at') CREATE INDEX idx_contact_inquiries_created_at ON contact_inquiries (created_at);
GO

-- --------------------------------------------------------------------------
-- company_assets
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'company_assets' AND type = N'U')
CREATE TABLE [company_assets] (
    [asset_key]     NVARCHAR(191) NOT NULL,
    [filename]      NVARCHAR(255) NULL,
    [extension]     NVARCHAR(255) NULL,
    [content_type]  NVARCHAR(255) NULL,
    [size]          INT NULL,
    [data]          VARBINARY(MAX) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [updated_by]    NVARCHAR(255) NULL,
    [created_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([asset_key])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_company_assets_asset_key') CREATE UNIQUE INDEX idx_company_assets_asset_key ON company_assets (asset_key);
GO

-- --------------------------------------------------------------------------
-- company_config
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'company_config' AND type = N'U')
CREATE TABLE [company_config] (
    [configId]      NVARCHAR(191) NOT NULL,
    [created_at]    DATETIME2(0) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([configId])
);
GO

-- --------------------------------------------------------------------------
-- payment_gateways
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'payment_gateways' AND type = N'U')
CREATE TABLE [payment_gateways] (
    [gatewayId]     NVARCHAR(191) NOT NULL,
    [created_at]    DATETIME2(0) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([gatewayId])
);
GO

-- --------------------------------------------------------------------------
-- data_sync_jobs
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'data_sync_jobs' AND type = N'U')
CREATE TABLE [data_sync_jobs] (
    [id]                NVARCHAR(191) NOT NULL,
    [entity]            NVARCHAR(MAX) NULL,
    [job_type]          NVARCHAR(MAX) NULL,
    [status]            NVARCHAR(255) NULL,
    [requested_by]      NVARCHAR(MAX) NULL,
    [source_filename]   NVARCHAR(MAX) NULL,
    [created_at]        DATETIME2(0) NULL,
    [updated_at]        DATETIME2(0) NULL,
    [started_at]        DATETIME2(0) NULL,
    [finished_at]       DATETIME2(0) NULL,
    [processed_rows]    INT NULL,
    [success_rows]      INT NULL,
    [failed_rows]       INT NULL,
    [payload_json]      NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_data_sync_jobs_created_at') CREATE INDEX idx_data_sync_jobs_created_at ON data_sync_jobs (created_at);
GO

-- --------------------------------------------------------------------------
-- role_permissions
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'role_permissions' AND type = N'U')
CREATE TABLE [role_permissions] (
    [role]          NVARCHAR(191) NOT NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([role])
);
GO

-- --------------------------------------------------------------------------
-- role_functionality_mappings
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'role_functionality_mappings' AND type = N'U')
CREATE TABLE [role_functionality_mappings] (
    [id]                    NVARCHAR(191) NOT NULL,
    [role]                  NVARCHAR(255) NULL,
    [functionality_code]    NVARCHAR(255) NULL,
    [created_at]            DATETIME2(0) NULL,
    [payload_json]          NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_role_functionality_unique') CREATE UNIQUE INDEX idx_role_functionality_unique ON role_functionality_mappings (role, functionality_code);
GO

-- --------------------------------------------------------------------------
-- user_role_mappings
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'user_role_mappings' AND type = N'U')
CREATE TABLE [user_role_mappings] (
    [id]            NVARCHAR(191) NOT NULL,
    [username]      NVARCHAR(255) NULL,
    [role]          NVARCHAR(255) NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_user_role_mappings_username') CREATE UNIQUE INDEX idx_user_role_mappings_username ON user_role_mappings (username);
GO

-- --------------------------------------------------------------------------
-- counters
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'counters' AND type = N'U')
CREATE TABLE [counters] (
    [counter_key]   NVARCHAR(191) NOT NULL,
    [seq]           INT NULL,
    [updated_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([counter_key])
);
GO
