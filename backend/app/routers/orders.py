import oracledb

from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import co_pool
from ..deps import get_current_user, require_role
from ..repositories import orders as repo
from ..repositories.orders import _replace_items
from ..schemas.common import Page
from ..schemas.orders import OrderCreate, OrderDetail, OrderOut, OrderUpdate
from ..seeding import orders as seed

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=Page[OrderOut])
def list_orders(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    status: str | None = None,
    customer_id: int | None = None,
    store_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    _u: dict = Depends(get_current_user),
):
    return repo.list_orders(page, pageSize, status, customer_id, store_id,
                            date_from, date_to)


@router.get("/generate", response_model=OrderCreate)
def generate(_u: dict = Depends(require_role("admin"))):
    return seed.generate_order()


@router.post("/bulk", status_code=201)
def bulk(count: int = Query(5, ge=1, le=1000), _u: dict = Depends(require_role("admin"))):
    inserted = 0
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        for _ in range(count):
            g = seed.generate_order()
            oid = cur.var(oracledb.NUMBER)
            cur.execute(
                "INSERT INTO orders (order_tms, customer_id, order_status, store_id) "
                "VALUES (:1, :2, :3, :4) RETURNING order_id INTO :5",
                (g["order_tms"], g["customer_id"], g["order_status"], g["store_id"], oid),
            )
            order_id = oid.getvalue()[0]
            _replace_items(cur, order_id, g["items"])
            inserted += 1
        conn.commit()
    return {"inserted": inserted}


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(order_id: int, _u: dict = Depends(get_current_user)):
    row = repo.get_order(order_id)
    if row is None:
        raise HTTPException(404, "Order not found")
    return row


@router.post("", response_model=OrderDetail, status_code=201)
def create_order(body: OrderCreate, _u: dict = Depends(require_role("admin"))):
    return repo.create_order(body)


@router.put("/{order_id}", response_model=OrderDetail)
def update_order(
    order_id: int, body: OrderUpdate, _u: dict = Depends(require_role("admin"))
):
    if repo.get_order(order_id) is None:
        raise HTTPException(404, "Order not found")
    return repo.update_order(order_id, body)


@router.delete("/{order_id}")
def delete_order(order_id: int, _u: dict = Depends(require_role("admin"))):
    if repo.get_order(order_id) is None:
        raise HTTPException(404, "Order not found")
    repo.delete_order(order_id)
    return {"deleted": True}
