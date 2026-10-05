import oracledb

from ..db import co_pool
from ..errors import ClientError
from ..schemas.orders import OrderCreate, OrderUpdate

_COLS = (
    "SELECT o.order_id, o.order_tms, o.customer_id, c.full_name AS customer_name, "
    "o.order_status, o.store_id, s.store_name, "
    "NVL((SELECT SUM(oi2.quantity * oi2.unit_price) FROM order_items oi2 "
    "     WHERE oi2.order_id = o.order_id), 0) AS total, "
    "(SELECT COUNT(*) FROM order_items oi3 WHERE oi3.order_id = o.order_id) AS item_count "
    "FROM orders o "
    "LEFT JOIN customers c ON c.customer_id = o.customer_id "
    "LEFT JOIN stores s ON s.store_id = o.store_id"
)

_KEYS = ["order_id", "order_tms", "customer_id", "customer_name", "order_status",
         "store_id", "store_name", "total", "item_count"]


def _row(r):
    return dict(zip(_KEYS, r))


def _where(status=None, customer_id=None, store_id=None, date_from=None, date_to=None):
    where, params = [], ()
    if status:
        where.append("o.order_status = :" + str(len(params) + 1)); params += (status,)
    if customer_id:
        where.append("o.customer_id = :" + str(len(params) + 1)); params += (customer_id,)
    if store_id:
        where.append("o.store_id = :" + str(len(params) + 1)); params += (store_id,)
    if date_from:
        where.append("o.order_tms >= :" + str(len(params) + 1)); params += (date_from,)
    if date_to:
        where.append("o.order_tms < :" + str(len(params) + 1)); params += (date_to,)
    return ("WHERE " + " AND ".join(where)) if where else "", params


def list_orders(page=1, page_size=20, status=None, customer_id=None, store_id=None,
                date_from=None, date_to=None):
    where_sql, params = _where(status, customer_id, store_id, date_from, date_to)
    page, page_size = max(1, page), min(200, max(1, page_size))
    offset = (page - 1) * page_size
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cc = conn.cursor()
        cc.execute(f"SELECT COUNT(*) FROM orders o {where_sql}", params)
        total = cc.fetchone()[0]
        cur.execute(
            f"{_COLS} {where_sql} ORDER BY o.order_tms DESC "
            f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY",
            params,
        )
        items = [_row(r) for r in cur.fetchall()]
        return {"items": items, "total": total, "page": page, "pageSize": page_size}


def get_order(order_id: int):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(f"{_COLS} WHERE o.order_id = :1", (order_id,))
        r = cur.fetchone()
        if r is None:
            return None
        header = _row(r)
        cur.execute(
            "SELECT line_item_id, product_id, quantity, unit_price "
            "FROM order_items WHERE order_id = :1 ORDER BY line_item_id",
            (order_id,),
        )
        header["items"] = [
            {
                "line_item_id": row[0],
                "product_id": row[1],
                "quantity": row[2],
                "unit_price": float(row[3]),
            }
            for row in cur.fetchall()
        ]
        return header


def _replace_items(cur, order_id, items):
    cur.execute("DELETE FROM order_items WHERE order_id = :1", (order_id,))
    for i, it in enumerate(items, start=1):
        cur.execute(
            "INSERT INTO order_items (order_id, line_item_id, product_id, unit_price, quantity) "
            "VALUES (:1, :2, :3, :4, :5)",
            (order_id, i, it.product_id, it.unit_price, it.quantity),
        )


def _map_error(exc):
    msg = str(exc)
    if "ORA-02291" in msg:
        raise ClientError(409, "FK_VIOLATION", "References a customer, store, or product that doesn't exist")
    raise ClientError(400, "DB_ERROR", msg)


def create_order(data: OrderCreate):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        oid = cur.var(oracledb.NUMBER)
        try:
            cur.execute(
                "INSERT INTO orders (order_tms, customer_id, order_status, store_id) "
                "VALUES (:1, :2, :3, :4) RETURNING order_id INTO :5",
                (data.order_tms, data.customer_id, data.order_status, data.store_id, oid),
            )
            order_id = oid.getvalue()[0]
            _replace_items(cur, order_id, data.items)
            conn.commit()
            return get_order(order_id)
        except Exception as exc:
            conn.rollback()
            _map_error(exc)


def update_order(order_id: int, data: OrderUpdate):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            fields = {}
            for k in ["customer_id", "store_id", "order_status", "order_tms"]:
                v = getattr(data, k)
                if v is not None:
                    fields[k] = v
            if fields:
                sets = ", ".join(f"{k} = :{i+1}" for i, k in enumerate(fields))
                cur.execute(
                    f"UPDATE orders SET {sets} WHERE order_id = :{len(fields)+1}",
                    list(fields.values()) + [order_id],
                )
            if data.items is not None:
                _replace_items(cur, order_id, data.items)
            conn.commit()
            return get_order(order_id)
        except Exception as exc:
            conn.rollback()
            _map_error(exc)


def delete_order(order_id: int) -> bool:
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM order_items WHERE order_id = :1", (order_id,))
            cur.execute("DELETE FROM orders WHERE order_id = :1", (order_id,))
            conn.commit()
            return cur.rowcount > 0 or True
        except Exception as exc:
            conn.rollback()
            raise ClientError(409, "FK_VIOLATION", str(exc))
