import oracledb

from ..db import co_pool
from ..errors import ClientError
from ..schemas.products import ProductCreate, ProductUpdate
from . import pagination


def _row(r):
    return {
        "product_id": r[0],
        "product_name": r[1],
        "unit_price": float(r[2]) if r[2] is not None else None,
    }


def list_products(page=1, page_size=20, search: str | None = None):
    where, params = "", ()
    if search:
        where = "WHERE LOWER(product_name) LIKE :1"
        params = (f"%{search.lower()}%",)
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        return pagination.run_page(
            cur,
            "SELECT product_id, product_name, unit_price",
            "products",
            where,
            "ORDER BY product_name",
            params,
            page,
            page_size,
        )


def get_product(pid: int):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT product_id, product_name, unit_price FROM products "
            "WHERE product_id = :1",
            (pid,),
        )
        r = cur.fetchone()
        return _row(r) if r else None


def create_product(data: ProductCreate):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        pid = cur.var(oracledb.NUMBER)
        try:
            cur.execute(
                "INSERT INTO products (product_name, unit_price) VALUES (:1, :2) "
                "RETURNING product_id INTO :3",
                (data.product_name, data.unit_price, pid),
            )
            conn.commit()
            return get_product(pid.getvalue()[0])
        except Exception as exc:
            conn.rollback()
            raise ClientError(400, "DB_ERROR", str(exc))


def update_product(pid: int, data: ProductUpdate):
    sets, params = [], ()
    if data.product_name is not None:
        sets.append("product_name = :" + str(len(params) + 1))
        params += (data.product_name,)
    if data.unit_price is not None:
        sets.append("unit_price = :" + str(len(params) + 1))
        params += (data.unit_price,)
    if not sets:
        return get_product(pid)
    params += (pid,)
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                f"UPDATE products SET {', '.join(sets)} WHERE product_id = :{len(params)}",
                params,
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise ClientError(400, "DB_ERROR", str(exc))
    return get_product(pid)


def delete_product(pid: int) -> bool:
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM products WHERE product_id = :1", (pid,))
            conn.commit()
            return cur.rowcount > 0
        except Exception as exc:
            conn.rollback()
            raise ClientError(
                409, "FK_VIOLATION", "Product is referenced by other data"
            )
