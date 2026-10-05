from datetime import date

from fastapi import APIRouter, Depends, Query

from ..deps import get_current_user
from ..repositories import metrics

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/revenue-over-time")
def revenue_over_time(
    granularity: str = Query("month", pattern="^(day|week|month)$"),
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
):
    return metrics.revenue_over_time(granularity, from_, to)


@router.get("/orders-by-status")
def orders_by_status(from_: date | None = Query(None, alias="from"), to: date | None = Query(None)):
    return metrics.orders_by_status(from_, to)


@router.get("/top-products")
def top_products(
    limit: int = Query(10, ge=1, le=100),
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
):
    return metrics.top_products(limit, from_, to)


@router.get("/revenue-by-store")
def revenue_by_store(from_: date | None = Query(None, alias="from"), to: date | None = Query(None)):
    return metrics.revenue_by_store(from_, to)


@router.get("/top-customers")
def top_customers(
    limit: int = Query(10, ge=1, le=100),
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
):
    return metrics.top_customers(limit, from_, to)


@router.get("/headcount-by-dept")
def headcount_by_dept():
    return metrics.headcount_by_dept()


@router.get("/salary-stats")
def salary_stats():
    return metrics.salary_stats()


@router.get("/hires-over-time")
def hires_over_time():
    return metrics.hires_over_time()
