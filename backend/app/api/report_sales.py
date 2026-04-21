"""Sales and purchase report routes."""
from fastapi import APIRouter, Depends, Query
from app.data.repository_providers import get_analytics_repository
from app.domain.contracts.analytics_repository import AnalyticsRepository
from app.api.ledger import get_current_admin
from datetime import datetime

router = APIRouter(prefix="/api/reports", tags=["Reports & Ledger"])


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


@router.get("/sales/")
async def get_sales_report(
    start_date: str = Query(None), end_date: str = Query(None),
    admin: str = Depends(get_current_admin),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
):
    """Get sales report (Admin only)"""
    return repo.sales_summary(
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )


@router.get("/purchases/")
async def get_purchase_report(
    start_date: str = Query(None), end_date: str = Query(None),
    admin: str = Depends(get_current_admin),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
):
    """Get purchase report (Admin only)"""
    return repo.purchase_summary(
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )


@router.get("/finances/")
async def get_company_finances(
    start_date: str = Query(None), end_date: str = Query(None),
    admin: str = Depends(get_current_admin),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
):
    """Get company finances report (Admin only)"""
    return repo.finance_summary(
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )
