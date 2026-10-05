import oracledb

from ..db import co_pool
from ..errors import ClientError
from ..schemas.customers import CustomerCreate, CustomerUpdate
from . import pagination


def _row(r):
    return {"customer_id": r[0], "email_address": r[1], "full_name": r[2]}


def _map_error(exc):
    msg = str(exc)
    if "ORA-00001" in msg:
        raise ClientError(409, "DUP_EMAIL", "A customer with that email already exists")
    if "ORA-02291" in msg or "ORA-02292" in msg:
        raise ClientError(
            409, "FK_VIOLATION", "This record is referenced by other data"
        )
    raise ClientError(400, "DB_ERROR", msg)


def list_customers(page=1, page_size=20, search: str | None = None):
    where, params = "", ()
    if search:
        where = "WHERE LOWER(full_name) LIKE :1 OR LOWER(email_address) LIKE :1"
        params = (f"%{search.lower()}%",)
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        return pagination.run_page(
            cur,
            "SELECT customer_id, email_address, full_name",
            "customers",
            where,
            "ORDER BY full_name",
            params,
            page,
            page_size,
        )


def get_customer(customer_id: int):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT customer_id, email_address, full_name FROM customers "
            "WHERE customer_id = :1",
            (customer_id,),
        )
        r = cur.fetchone()
        return _row(r) if r else None


def create_customer(data: CustomerCreate):
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cid = cur.var(oracledb.NUMBER)
        try:
            cur.execute(
                "INSERT INTO customers (email_address, full_name) VALUES (:1, :2) "
                "RETURNING customer_id INTO :3",
                (data.email_address, data.full_name, cid),
            )
            conn.commit()
            return get_customer(cid.getvalue()[0])
        except Exception as exc:
            conn.rollback()
            _map_error(exc)


def update_customer(customer_id: int, data: CustomerUpdate):
    sets, params = [], ()
    if data.full_name is not None:
        sets.append("full_name = :" + str(len(params) + 1))
        params += (data.full_name,)
    if data.email_address is not None:
        sets.append("email_address = :" + str(len(params) + 1))
        params += (data.email_address,)
    if not sets:
        return get_customer(customer_id)
    params += (customer_id,)
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                f"UPDATE customers SET {', '.join(sets)} WHERE customer_id = :{len(params)}",
                params,
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            _map_error(exc)
    return get_customer(customer_id)


def delete_customer(customer_id: int) -> bool:
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM customers WHERE customer_id = :1", (customer_id,))
            conn.commit()
            return cur.rowcount > 0
        except Exception as exc:
            conn.rollback()
            _map_error(exc)
