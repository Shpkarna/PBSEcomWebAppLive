-- Phase 6 standalone MySQL log schema.
--
-- Default database name matches backend/app/config.py (`log_database=logDB`).
-- If your deployment uses a different DB name, replace `logDB` before running.

CREATE DATABASE IF NOT EXISTS `logDB`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `logDB`;

CREATE TABLE IF NOT EXISTS `audit_logs` (
  `id` VARCHAR(191) NOT NULL,
  `action` VARCHAR(255) NULL,
  `user` VARCHAR(255) NULL,
  `path` VARCHAR(255) NULL,
  `immutable` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` DATETIME NULL,
  `payload_json` LONGTEXT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_audit_logs_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;