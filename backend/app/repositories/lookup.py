from ..db import co_pool, hr_pool


def _rows(pool, sql, params=()):
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def departments():
    return _rows(hr_pool(), "SELECT department_id, department_name FROM departments ORDER BY department_name")


def jobs():
    return _rows(hr_pool(), "SELECT job_id, job_title FROM jobs ORDER BY job_title")


def managers():
    return _rows(hr_pool(), "SELECT employee_id, first_name || ' ' || last_name AS name FROM employees ORDER BY name")


def locations():
    return _rows(hr_pool(), "SELECT location_id, city FROM locations ORDER BY city")


def countries():
    return _rows(hr_pool(), "SELECT country_id, country_name FROM countries ORDER BY country_name")


def regions():
    return _rows(hr_pool(), "SELECT region_id, region_name FROM regions ORDER BY region_id")


def stores():
    return _rows(co_pool(), "SELECT store_id, store_name FROM stores ORDER BY store_name")


def order_statuses():
    return _rows(co_pool(), "SELECT DISTINCT order_status FROM orders ORDER BY order_status")


def products_compact():
    return _rows(co_pool(), "SELECT product_id, product_name, unit_price FROM products ORDER BY product_name")


def customers_compact():
    return _rows(co_pool(), "SELECT customer_id, full_name FROM customers ORDER BY full_name")
