"""Stock, customer, and vendor report routes."""
from fastapi import APIRouter, Depends
from app.data.repository_providers import get_analytics_repository
from app.domain.contracts.analytics_repository import AnalyticsRepository
from app.api.ledger import get_current_admin

router = APIRouter(prefix="/api/reports", tags=["Reports & Ledger"])


@router.get("/stock/")
async def get_stock_report(
    admin: str = Depends(get_current_admin),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
):
    """Get stock report (Admin only)"""
    return repo.stock_summary()


@router.get("/customers/")
async def get_customer_report(
    admin: str = Depends(get_current_admin),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
):
    """Get customer report (Admin only)"""
    return repo.customer_summary()


@router.get("/vendors/")
async def get_vendor_report(
    admin: str = Depends(get_current_admin),
    repo: AnalyticsRepository = Depends(get_analytics_repository),
):
    """Get vendor report (Admin only)"""
    return repo.vendor_summary()
