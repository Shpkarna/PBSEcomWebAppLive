#!/usr/bin/env bash
# mysql-init.sh
# Runs ONCE inside the MySQL container on first start (docker-entrypoint-initdb.d).
#
# Responsibilities:
#   1. Create the audit-log database (ecomdb_phase6_log).
#   2. Create the application user (MYSQL_APP_USER) with a strong password.
#   3. Grant ALL PRIVILEGES on both databases to the application user.
#
# Environment variables are injected by docker-compose.mysql.yml:
#   MYSQL_ROOT_PASSWORD  — set by the MySQL Docker image
#   MYSQL_APP_USER       — application DB user (e.g. ecom_app)
#   MYSQL_APP_PASSWORD   — application DB password
#   MYSQL_DATABASE       — primary app database (already created by Docker image)
#   LOG_DATABASE         — audit/log database (created here)
#
# SECURITY NOTES:
#   - Runs as root inside the container; never expose the root password outside.
#   - The app user is granted only what it needs (both app databases).
#   - Do not add SUPER or GRANT OPTION to the app user.

set -euo pipefail

APP_USER="${MYSQL_APP_USER:-ecom_app}"
APP_PASS="${MYSQL_APP_PASSWORD:?MYSQL_APP_PASSWORD must be set in .env.mysql}"
APP_DB="${MYSQL_DATABASE:-ecomdb_phase6}"
LOG_DB="${LOG_DATABASE:-ecomdb_phase6_log}"

echo "[mysql-init] Provisioning databases and application user..."

mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
    -- ── Log / audit database ──────────────────────────────────────────────
    CREATE DATABASE IF NOT EXISTS \`${LOG_DB}\`
        CHARACTER SET utf8mb4
        COLLATE utf8mb4_unicode_ci;

    -- ── Application user ─────────────────────────────────────────────────
    -- Use CREATE USER IF NOT EXISTS so re-running the script is idempotent.
    CREATE USER IF NOT EXISTS '${APP_USER}'@'%'
        IDENTIFIED WITH mysql_native_password BY '${APP_PASS}';

    -- Update password if the user already existed with a different one.
    ALTER USER '${APP_USER}'@'%'
        IDENTIFIED WITH mysql_native_password BY '${APP_PASS}';

    -- ── Grants ───────────────────────────────────────────────────────────
    GRANT ALL PRIVILEGES ON \`${APP_DB}\`.*  TO '${APP_USER}'@'%';
    GRANT ALL PRIVILEGES ON \`${LOG_DB}\`.*  TO '${APP_USER}'@'%';

    FLUSH PRIVILEGES;
EOSQL

echo "[mysql-init] Done."
echo "[mysql-init]   App database : ${APP_DB}"
echo "[mysql-init]   Log database : ${LOG_DB}"
echo "[mysql-init]   App user     : ${APP_USER}@%"
