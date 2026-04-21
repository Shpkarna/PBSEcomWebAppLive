"""Dependency providers for repository contracts.

Phase 2 introduced thin composition points.  Phase 4 delegates to the
driver registry so providers return the correct implementation for the
configured ``db_engine`` without any hardcoded Mongo imports.
"""
from app.data.driver_registry import (
    resolve_analytics_repository,
    resolve_auth_repository,
    resolve_bootstrap,
    resolve_ledger_repository,
    resolve_log_repository,
    resolve_order_cart_repository,
    resolve_product_repository,
    resolve_report_repository,
    resolve_utility_repository,
)
from app.domain.contracts.analytics_repository import AnalyticsRepository
from app.domain.contracts.auth_repository import AuthRepository
from app.domain.contracts.database_bootstrap import DatabaseBootstrap
from app.domain.contracts.ledger_repository import LedgerRepository
from app.domain.contracts.log_repository import LogRepository
from app.domain.contracts.order_cart_repository import OrderCartRepository
from app.domain.contracts.product_repository import ProductRepository
from app.domain.contracts.report_repository import ReportRepository
from app.domain.contracts.utility_repository import UtilityRepository


def get_product_repository() -> ProductRepository:
    """Return product repository for the active database engine."""
    return resolve_product_repository()


def get_auth_repository() -> AuthRepository:
    """Return auth repository for the active database engine."""
    return resolve_auth_repository()


def get_order_cart_repository() -> OrderCartRepository:
    """Return cart/order repository for the active database engine."""
    return resolve_order_cart_repository()


def get_utility_repository() -> UtilityRepository:
    """Return utility repository for the active database engine."""
    return resolve_utility_repository()


def get_ledger_repository() -> LedgerRepository:
    """Return ledger repository for the active database engine."""
    return resolve_ledger_repository()


def get_report_repository() -> ReportRepository:
    """Return report repository for the active database engine."""
    return resolve_report_repository()


def get_analytics_repository() -> AnalyticsRepository:
    """Return analytics repository for the active database engine."""
    return resolve_analytics_repository()


def get_database_bootstrap() -> DatabaseBootstrap:
    """Return database bootstrap for the active database engine."""
    return resolve_bootstrap()


def get_log_repository() -> LogRepository:
    """Return audit log repository for the active database engine."""
    return resolve_log_repository()
