from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from ..deps import get_current_user
from ..errors import ClientError
from ..exporters import to_csv, to_xlsx
from ..repositories import customers as cust
from ..repositories import employees as emp
from ..repositories import orders as ordr
from ..repositories import products as prod
from ..repositories.pagination import clamp

router = APIRouter(
    prefix="/export",
    tags=["export"],
    dependencies=[Depends(get_current_user)],
)


def _fetch(entity: str, page: int, page_size: int, f: dict) -> list[dict]:
    if entity == "customers":
        return cust.list_customers(page, page_size, f.get("search"))["items"]
    if entity == "products":
        return prod.list_products(page, page_size, f.get("search"))["items"]
    if entity == "employees":
        return emp.list_employees(
            page, page_size, f.get("department_id"), f.get("job_id"), f.get("search")
        )["items"]
    if entity == "orders":
        return ordr.list_orders(
            page, page_size, f.get("status"), f.get("customer_id"),
            f.get("store_id"), f.get("date_from"), f.get("date_to"),
        )["items"]
    raise ClientError(404, "UNKNOWN_ENTITY", f"Unknown export entity: {entity}")


@router.get("/{entity}")
def export(
    entity: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=1000),
    search: str | None = None,
    status: str | None = None,
    customer_id: int | None = None,
    store_id: int | None = None,
    department_id: int | None = None,
    job_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    filters = {
        "search": search, "status": status, "customer_id": customer_id,
        "store_id": store_id, "department_id": department_id,
        "job_id": job_id, "date_from": date_from, "date_to": date_to,
    }
    _p, _ps = clamp(page, pageSize)
    rows = _fetch(entity, _p, _ps, filters)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if format == "csv":
        data = to_csv(rows)
        media = "text/csv; charset=utf-8"
    else:
        data = to_xlsx(rows)
        media = (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    headers = {
        "Content-Disposition": f"attachment; filename={entity}_{stamp}.{format}"
    }
    return Response(content=data, media_type=media, headers=headers)
