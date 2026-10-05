from datetime import datetime, timedelta

from faker import Faker

from ..db import co_pool

_fake = Faker()
STATUSES = ["OPEN", "PENDING", "COMPLETE", "CANCELLED"]


def _lookups():
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute("SELECT customer_id FROM customers")
        custs = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT store_id FROM stores")
        stores = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT product_id, unit_price FROM products")
        prods = cur.fetchall()
    return custs, stores, prods


def generate_order() -> dict:
    custs, stores, prods = _lookups()
    n = _fake.random_int(1, 4)
    items = []
    for _ in range(n):
        p, price = _fake.random.choice(prods) if prods else (1, 10.0)
        items.append({
            "product_id": p,
            "quantity": _fake.random_int(1, 20),
            "unit_price": float(price),
        })
    return {
        "customer_id": _fake.random.choice(custs) if custs else 1,
        "store_id": _fake.random.choice(stores) if stores else 1,
        "order_status": _fake.random.choice(STATUSES),
        "order_tms": datetime.now() - timedelta(days=_fake.random_int(0, 365)),
        "items": items,
    }
