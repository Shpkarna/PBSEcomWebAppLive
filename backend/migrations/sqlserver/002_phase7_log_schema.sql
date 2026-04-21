-- Phase 7 SQL Server audit log schema.
--
-- Default database name matches backend/app/config.py defaults:
--   mssql_log_database = ecomdb_log
-- Run against SQL Server 2017+ (or Express edition on localhost\SQLEXPRESS).
--
-- Usage:
--   sqlcmd -S localhost\SQLEXPRESS -E -i 002_phase7_log_schema.sql

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = N'ecomdb_log')
    EXEC('CREATE DATABASE [ecomdb_log] COLLATE Latin1_General_CI_AS');
GO

USE [ecomdb_log];
GO

-- --------------------------------------------------------------------------
-- audit_logs
-- --------------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.objects WHERE name = N'audit_logs' AND type = N'U')
CREATE TABLE [audit_logs] (
    [id]            NVARCHAR(191) NOT NULL,
    [action]        NVARCHAR(255) NULL,
    [user]          NVARCHAR(255) NULL,
    [path]          NVARCHAR(255) NULL,
    [immutable]     BIT NOT NULL DEFAULT 0,
    [created_at]    DATETIME2(0) NULL,
    [payload_json]  NVARCHAR(MAX) NULL,
    PRIMARY KEY ([id])
);
GO
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = N'idx_audit_logs_created_at')
    CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at);
GO
