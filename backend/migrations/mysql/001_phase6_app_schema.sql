-- Phase 6 standalone MySQL application schema.
--
-- Default database name matches backend/app/config.py (`mysql_database=ecomdb`).
-- If your deployment uses a different DB name, replace `ecomdb` before running.

CREATE DATABASE IF NOT EXISTS `ecomdb`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `ecomdb`;

CREATE TABLE IF NOT EXISTS `users` (
  `id` VARCHAR(191) NOT NULL,
  `username` VARCHAR(255) NULL,
  `email` VARCHAR(255) NULL,
  `password_hash` VARCHAR(255) NULL,
  `full_name` VARCHAR(255) NULL,
  `phone` VARCHAR(255) NULL,
  `dob` VARCHAR(255) NULL,
  `sex` VARCHAR(255) NULL,
  `marital_status` VARCHAR(255) NULL,
  `address` LONGTEXT NULL,
  `role` VARCHAR(255) NULL,
  `customer_id` VARCHAR(255) NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 0,
  `phone_verified` TINYINT(1) NOT NULL DEFAULT 0,
  `email_verified` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_users_username` (`username`),
  UNIQUE KEY `idx_users_email` (`email`),
  UNIQUE KEY `idx_users_customer_id` (`customer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `sessions` (
  `id` VARCHAR(191) NOT NULL,
  `username` VARCHAR(255) NULL,
  `client_ip` VARCHAR(255) NULL,
  `client_mac` VARCHAR(255) NULL,
  `access_token` LONGTEXT NULL,
  `token_expires_at` DATETIME NULL,
  `created_at` DATETIME NULL,
  `expires_at` DATETIME NULL,
  `last_activity` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_sessions_username` (`username`),
  KEY `idx_sessions_expires_at` (`expires_at`),
  KEY `idx_sessions_identity` (`username`, `client_ip`, `client_mac`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `email_verifications` (
  `id` VARCHAR(191) NOT NULL,
  `username` VARCHAR(255) NULL,
  `token` VARCHAR(255) NULL,
  `verified` TINYINT(1) NOT NULL DEFAULT 0,
  `verified_at` DATETIME NULL,
  `expires_at` DATETIME NULL,
  `created_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `otp_records` (
  `id` VARCHAR(191) NOT NULL,
  `phone` VARCHAR(255) NULL,
  `purpose` VARCHAR(255) NULL,
  `otp` VARCHAR(255) NULL,
  `created_at` DATETIME NULL,
  `expires_at` DATETIME NULL,
  `verified` TINYINT(1) NOT NULL DEFAULT 0,
  `verified_at` DATETIME NULL,
  `used` TINYINT(1) NOT NULL DEFAULT 0,
  `used_at` DATETIME NULL,
  `verification_attempts` INT NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `products` (
  `id` VARCHAR(191) NOT NULL,
  `sku` VARCHAR(255) NULL,
  `name` VARCHAR(255) NULL,
  `barcode` VARCHAR(255) NULL,
  `description` LONGTEXT NULL,
  `category` VARCHAR(255) NULL,
  `stock_price` DECIMAL(12,2) NULL,
  `sell_price` DECIMAL(12,2) NULL,
  `discount` VARCHAR(255) NULL,
  `discount_value` DECIMAL(12,2) NULL,
  `discount_type` VARCHAR(255) NULL,
  `stock_quantity` INT NULL,
  `gst_rate` DECIMAL(12,4) NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_products_sku` (`sku`),
  KEY `idx_products_barcode` (`barcode`),
  KEY `idx_products_created_at` (`created_at`),
  KEY `idx_products_name` (`name`),
  KEY `idx_products_sell_price` (`sell_price`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `product_media` (
  `id` VARCHAR(191) NOT NULL,
  `product_id` VARCHAR(255) NULL,
  `filename` VARCHAR(255) NULL,
  `content_type` VARCHAR(255) NULL,
  `media_type` VARCHAR(255) NULL,
  `size` INT NULL,
  `created_at` DATETIME NULL,
  `created_by` VARCHAR(255) NULL,
  `data` LONGBLOB NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_product_media_product_created` (`product_id`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `cart_items` (
  `id` VARCHAR(191) NOT NULL,
  `user_id` LONGTEXT NULL,
  `session_id` LONGTEXT NULL,
  `product_id` VARCHAR(255) NULL,
  `product_name` VARCHAR(255) NULL,
  `quantity` INT NULL,
  `price` DECIMAL(12,2) NULL,
  `gst_rate` DECIMAL(12,4) NULL,
  `cart_quote_id` VARCHAR(255) NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `categories` (
  `id` VARCHAR(191) NOT NULL,
  `name` VARCHAR(255) NULL,
  `description` LONGTEXT NULL,
  `discount_type` VARCHAR(255) NULL,
  `discount_value` DECIMAL(12,2) NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_categories_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `orders` (
  `id` VARCHAR(191) NOT NULL,
  `customer_id` VARCHAR(255) NULL,
  `order_number` VARCHAR(255) NULL,
  `cart_quote_id` VARCHAR(255) NULL,
  `subtotal` DECIMAL(12,2) NULL,
  `total_discount` DECIMAL(12,2) NULL,
  `total_gst` DECIMAL(12,2) NULL,
  `total` DECIMAL(12,2) NULL,
  `payment_method` VARCHAR(255) NULL,
  `payment_status` VARCHAR(255) NULL,
  `payment_provider` VARCHAR(255) NULL,
  `payment_reference` VARCHAR(255) NULL,
  `razorpay_order_id` VARCHAR(255) NULL,
  `status` VARCHAR(255) NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_orders_customer_created` (`customer_id`, `created_at`),
  KEY `idx_orders_order_number` (`order_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `ledger_entries` (
  `id` VARCHAR(191) NOT NULL,
  `transaction_type` VARCHAR(255) NULL,
  `category` VARCHAR(255) NULL,
  `amount` DECIMAL(12,2) NULL,
  `reference_id` LONGTEXT NULL,
  `notes` LONGTEXT NULL,
  `created_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_ledger_entries_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `stock_ledger` (
  `id` VARCHAR(191) NOT NULL,
  `product_id` VARCHAR(255) NULL,
  `transaction_type` VARCHAR(255) NULL,
  `quantity` INT NULL,
  `reference` VARCHAR(255) NULL,
  `notes` LONGTEXT NULL,
  `created_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_stock_ledger_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `payments` (
  `id` VARCHAR(191) NOT NULL,
  `provider` VARCHAR(255) NULL,
  `status` VARCHAR(255) NULL,
  `username` VARCHAR(255) NULL,
  `customer_id` VARCHAR(255) NULL,
  `payment_method` VARCHAR(255) NULL,
  `razorpay_order_id` VARCHAR(255) NULL,
  `razorpay_payment_id` VARCHAR(255) NULL,
  `razorpay_signature` VARCHAR(255) NULL,
  `amount` INT NULL,
  `currency` VARCHAR(255) NULL,
  `receipt` VARCHAR(255) NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `checkout_locks` (
  `cart_quote_id` VARCHAR(191) NOT NULL,
  `session_id` LONGTEXT NULL,
  `expires_at` DATETIME NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`cart_quote_id`),
  UNIQUE KEY `idx_checkout_locks_cart_quote_id` (`cart_quote_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `vendors` (
  `id` VARCHAR(191) NOT NULL,
  `name` VARCHAR(255) NULL,
  `email` VARCHAR(255) NULL,
  `phone` VARCHAR(255) NULL,
  `address` LONGTEXT NULL,
  `gst_number` LONGTEXT NULL,
  `bank_details` LONGTEXT NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_vendors_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `saved_products` (
  `id` VARCHAR(191) NOT NULL,
  `customer_id` VARCHAR(255) NULL,
  `product_id` VARCHAR(255) NULL,
  `saved_price` DECIMAL(12,2) NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `contact_inquiries` (
  `id` VARCHAR(191) NOT NULL,
  `name` VARCHAR(255) NULL,
  `email` VARCHAR(255) NULL,
  `phone` VARCHAR(255) NULL,
  `subject` LONGTEXT NULL,
  `message` LONGTEXT NULL,
  `status` VARCHAR(255) NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_contact_inquiries_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `company_assets` (
  `asset_key` VARCHAR(191) NOT NULL,
  `filename` VARCHAR(255) NULL,
  `extension` VARCHAR(255) NULL,
  `content_type` VARCHAR(255) NULL,
  `size` INT NULL,
  `data` LONGBLOB NULL,
  `updated_at` DATETIME NULL,
  `updated_by` VARCHAR(255) NULL,
  `created_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`asset_key`),
  UNIQUE KEY `idx_company_assets_asset_key` (`asset_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `company_config` (
  `configId` VARCHAR(191) NOT NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`configId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `payment_gateways` (
  `gatewayId` VARCHAR(191) NOT NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`gatewayId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `data_sync_jobs` (
  `id` VARCHAR(191) NOT NULL,
  `entity` LONGTEXT NULL,
  `job_type` LONGTEXT NULL,
  `status` VARCHAR(255) NULL,
  `requested_by` LONGTEXT NULL,
  `source_filename` LONGTEXT NULL,
  `created_at` DATETIME NULL,
  `updated_at` DATETIME NULL,
  `started_at` DATETIME NULL,
  `finished_at` DATETIME NULL,
  `processed_rows` INT NULL,
  `success_rows` INT NULL,
  `failed_rows` INT NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_data_sync_jobs_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `role_permissions` (
  `role` VARCHAR(191) NOT NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `role_functionality_mappings` (
  `id` VARCHAR(191) NOT NULL,
  `role` VARCHAR(255) NULL,
  `functionality_code` VARCHAR(255) NULL,
  `created_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_role_functionality_unique` (`role`, `functionality_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `user_role_mappings` (
  `id` VARCHAR(191) NOT NULL,
  `username` VARCHAR(255) NULL,
  `role` VARCHAR(255) NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_user_role_mappings_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `counters` (
  `counter_key` VARCHAR(191) NOT NULL,
  `seq` INT NULL,
  `updated_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`counter_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;