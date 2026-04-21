"""Driver registry — resolves repository implementations based on ``settings.db_engine``.

Phase 4 artifact.  Each engine is represented by a *driver module* that
provides concrete implementations for every repository contract.  The
registry validates the selected engine at startup and exposes typed
factory helpers consumed by ``repository_providers``.

Supported engines
-----------------
- ``mongodb`` — default, uses ``backend/app/data/repositories/mongo_*.py``
- ``mysql`` — Phase 6 implementation, uses ``backend/app/data/repositories/mysql_*.py``
- ``sqlserver`` — placeholder, raises on startup until Phase 7
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from app.domain.contracts.analytics_repository import AnalyticsRepository
    from app.domain.contracts.auth_repository import AuthRepository
    from app.domain.contracts.database_bootstrap import DatabaseBootstrap
    from app.domain.contracts.ledger_repository import LedgerRepository
    from app.domain.contracts.log_repository import LogRepository
    from app.domain.contracts.order_cart_repository import OrderCartRepository
    from app.domain.contracts.product_repository import ProductRepository
    from app.domain.contracts.report_repository import ReportRepository
    from app.domain.contracts.utility_repository import UtilityRepository


# ---------------------------------------------------------------------------
# Internal: engine → concrete class mapping (lazy-imported to avoid pulling
# in pymongo / mysql / pyodbc at import time when the engine is not selected).
# ---------------------------------------------------------------------------

def _mongo_classes() -> dict:
    """Return mapping of contract name → Mongo concrete class."""
    from app.data.repositories.mongo_analytics_repository import MongoAnalyticsRepository
    from app.data.repositories.mongo_auth_repository import MongoAuthRepository
    from app.data.repositories.mongo_bootstrap import MongoBootstrap
    from app.data.repositories.mongo_ledger_repository import MongoLedgerRepository
    from app.data.repositories.mongo_log_repository import MongoLogRepository
    from app.data.repositories.mongo_order_cart_repository import MongoOrderCartRepository
    from app.data.repositories.mongo_product_repository import MongoProductRepository
    from app.data.repositories.mongo_report_repository import MongoReportRepository
    from app.data.repositories.mongo_utility_repository import MongoUtilityRepository

    return {
        "analytics": MongoAnalyticsRepository,
        "auth": MongoAuthRepository,
        "bootstrap": MongoBootstrap,
        "ledger": MongoLedgerRepository,
        "log": MongoLogRepository,
        "order_cart": MongoOrderCartRepository,
        "product": MongoProductRepository,
        "report": MongoReportRepository,
        "utility": MongoUtilityRepository,
    }


def _mysql_classes() -> dict:
    """Return mapping of contract name -> MySQL concrete class."""
    from app.data.repositories.mysql_analytics_repository import MySQLAnalyticsRepository
    from app.data.repositories.mysql_auth_repository import MySQLAuthRepository
    from app.data.repositories.mysql_bootstrap import MySQLBootstrap
    from app.data.repositories.mysql_ledger_repository import MySQLLedgerRepository
    from app.data.repositories.mysql_log_repository import MySQLLogRepository
    from app.data.repositories.mysql_order_cart_repository import MySQLOrderCartRepository
    from app.data.repositories.mysql_product_repository import MySQLProductRepository
    from app.data.repositories.mysql_report_repository import MySQLReportRepository
    from app.data.repositories.mysql_utility_repository import MySQLUtilityRepository

    return {
        "analytics": MySQLAnalyticsRepository,
        "auth": MySQLAuthRepository,
        "bootstrap": MySQLBootstrap,
        "ledger": MySQLLedgerRepository,
        "log": MySQLLogRepository,
        "order_cart": MySQLOrderCartRepository,
        "product": MySQLProductRepository,
        "report": MySQLReportRepository,
        "utility": MySQLUtilityRepository,
    }


def _sqlserver_classes() -> dict:
    """Return mapping of contract name -> SQL Server concrete class (Phase 7)."""
    from app.data.repositories.mssql_analytics_repository import MSSQLAnalyticsRepository
    from app.data.repositories.mssql_auth_repository import MSSQLAuthRepository
    from app.data.repositories.mssql_bootstrap import MSSQLBootstrap
    from app.data.repositories.mssql_ledger_repository import MSSQLLedgerRepository
    from app.data.repositories.mssql_log_repository import MSSQLLogRepository
    from app.data.repositories.mssql_order_cart_repository import MSSQLOrderCartRepository
    from app.data.repositories.mssql_product_repository import MSSQLProductRepository
    from app.data.repositories.mssql_report_repository import MSSQLReportRepository
    from app.data.repositories.mssql_utility_repository import MSSQLUtilityRepository

    return {
        "analytics": MSSQLAnalyticsRepository,
        "auth": MSSQLAuthRepository,
        "bootstrap": MSSQLBootstrap,
        "ledger": MSSQLLedgerRepository,
        "log": MSSQLLogRepository,
        "order_cart": MSSQLOrderCartRepository,
        "product": MSSQLProductRepository,
        "report": MSSQLReportRepository,
        "utility": MSSQLUtilityRepository,
    }


_ENGINE_LOADERS = {
    "mongodb": _mongo_classes,
    "mysql": _mysql_classes,
    "sqlserver": _sqlserver_classes,
}
SUPPORTED_ENGINES = ("mongodb", "mysql", "sqlserver")

# Cached mapping after first ``_resolve()`` call.
_resolved: dict | None = None


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------

class EngineConfigError(RuntimeError):
    """Raised when the selected engine is missing required configuration."""


def _validate_engine_config() -> None:
    """Fail fast if the selected engine has missing connection settings."""
    engine = settings.db_engine

    if engine not in SUPPORTED_ENGINES:
        raise EngineConfigError(
            f"Unsupported db_engine '{engine}'. "
            f"Supported values: {', '.join(SUPPORTED_ENGINES)}."
        )

    if engine == "mongodb":
        if not settings.mongodb_url:
            raise EngineConfigError(
                "db_engine is 'mongodb' but MONGODB_URL is empty.  "
                "Set environment variable MONGODB_URL or add it to backend/.env. "
                "If this is a fresh install, run 'python backend/setup_db_engine.py --engine mongodb'."
            )
        if engine not in _ENGINE_LOADERS:
            raise EngineConfigError("MongoDB driver registry is not configured.")
    elif engine == "mysql":
        missing = []
        if not settings.mysql_host:
            missing.append("MYSQL_HOST")
        if not settings.mysql_user:
            missing.append("MYSQL_USER")
        if not settings.mysql_database:
            missing.append("MYSQL_DATABASE")
        if int(settings.mysql_port) <= 0:
            missing.append("MYSQL_PORT")
        if missing:
            raise EngineConfigError(
                "db_engine is 'mysql' but required MySQL settings are missing or invalid: "
                f"{', '.join(missing)}. "
                "Set them in backend/.env or run 'python backend/setup_db_engine.py --engine mysql'."
            )
        if engine not in _ENGINE_LOADERS:
            raise EngineConfigError("MySQL driver registry is not configured.")
    elif engine == "sqlserver":
        missing = []
        if not settings.mssql_server:
            missing.append("MSSQL_SERVER")
        if not settings.mssql_driver:
            missing.append("MSSQL_DRIVER")
        if not settings.mssql_database:
            missing.append("MSSQL_DATABASE")
        if missing:
            raise EngineConfigError(
                "db_engine is 'sqlserver' but required SQL Server settings are missing or invalid: "
                f"{', '.join(missing)}. "
                "Set them in backend/.env or run 'python backend/setup_db_engine.py --engine sqlserver'."
            )
        if engine not in _ENGINE_LOADERS:
            raise EngineConfigError("SQL Server driver registry is not configured.")


def _resolve() -> dict:
    """Validate configuration, load the engine module, and cache it."""
    global _resolved
    if _resolved is not None:
        return _resolved

    _validate_engine_config()
    loader = _ENGINE_LOADERS[settings.db_engine]
    _resolved = loader()
    return _resolved


# ---------------------------------------------------------------------------
# Public factory helpers — called from repository_providers.py
# ---------------------------------------------------------------------------

def resolve_auth_repository() -> "AuthRepository":
    return _resolve()["auth"]()


def resolve_bootstrap() -> "DatabaseBootstrap":
    return _resolve()["bootstrap"]()


def resolve_ledger_repository() -> "LedgerRepository":
    return _resolve()["ledger"]()


def resolve_log_repository() -> "LogRepository":
    return _resolve()["log"]()


def resolve_order_cart_repository() -> "OrderCartRepository":
    return _resolve()["order_cart"]()


def resolve_product_repository() -> "ProductRepository":
    return _resolve()["product"]()


def resolve_report_repository() -> "ReportRepository":
    return _resolve()["report"]()


def resolve_utility_repository() -> "UtilityRepository":
    return _resolve()["utility"]()


def resolve_analytics_repository() -> "AnalyticsRepository":
    return _resolve()["analytics"]()


def resolve_shutdown() -> callable:
    """Return the engine-specific shutdown callable.

    For Mongo this closes the shared client; future engines will close
    their own connection pools.
    """
    engine = settings.db_engine
    if engine == "mongodb":
        from app.database import close_mongo_connection
        return close_mongo_connection
    if engine == "mysql":
        from app.data.mysql_client import close_mysql_connections
        return close_mysql_connections
    if engine == "sqlserver":
        from app.data.mssql_client import close_mssql_connections
        return close_mssql_connections
    return lambda: None


def current_engine() -> str:
    """Return the active engine name (for diagnostics / health check)."""
    return settings.db_engine
