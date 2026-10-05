from ..db import co_pool, hr_pool


def _q(pool, sql, params=()):
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _trunc(granularity: str) -> str:
    return {
        "day": "TRUNC(o.order_tms, 'DD')",
        "week": "TRUNC(o.order_tms, 'IW')",
        "month": "TRUNC(o.order_tms, 'MM')",
    }[granularity]


def _range_where(date_from=None, date_to=None):
    params = []
    where = ""
    if date_from:
        where += " AND o.order_tms >= :1"
        params.append(date_from)
    if date_to:
        where += f" AND o.order_tms < :{len(params) + 1}"
        params.append(date_to)
    return where, tuple(params)


def revenue_over_time(granularity, date_from, date_to):
    where, params = _range_where(date_from, date_to)
    sql = (
        f"SELECT {_trunc(granularity)} AS period, "
        f"SUM(oi.quantity * oi.unit_price) AS revenue "
        f"FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
        f"WHERE 1=1 {where} GROUP BY {_trunc(granularity)} ORDER BY period"
    )
    rows = _q(co_pool(), sql, params)
    return {
        "points": [
            {
                "period": r["period"].isoformat() if r["period"] else None,
                "revenue": float(r["revenue"] or 0),
            }
            for r in rows
        ]
    }


def orders_by_status(date_from, date_to):
    where, params = _range_where(date_from, date_to)
    sql = (
        f"SELECT o.order_status, COUNT(*) AS cnt FROM orders o WHERE 1=1 {where} "
        f"GROUP BY o.order_status ORDER BY cnt DESC"
    )
    rows = _q(co_pool(), sql, params)
    return {"series": [{"status": r["order_status"], "count": r["cnt"]} for r in rows]}


def top_products(limit, date_from, date_to):
    where, params = _range_where(date_from, date_to)
    sql = (
        f"SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS revenue, "
        f"SUM(oi.quantity) AS qty FROM order_items oi "
        f"JOIN orders o ON o.order_id = oi.order_id "
        f"JOIN products p ON p.product_id = oi.product_id "
        f"WHERE 1=1 {where} GROUP BY p.product_name ORDER BY revenue DESC "
        f"FETCH FIRST {int(limit)} ROWS ONLY"
    )
    rows = _q(co_pool(), sql, params)
    return {
        "series": [
            {
                "product_name": r["product_name"],
                "revenue": float(r["revenue"] or 0),
                "qty": int(r["qty"] or 0),
            }
            for r in rows
        ]
    }


def revenue_by_store(date_from, date_to):
    where, params = _range_where(date_from, date_to)
    sql = (
        f"SELECT s.store_name, SUM(oi.quantity * oi.unit_price) AS revenue "
        f"FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
        f"JOIN stores s ON s.store_id = o.store_id WHERE 1=1 {where} "
        f"GROUP BY s.store_name ORDER BY revenue DESC"
    )
    rows = _q(co_pool(), sql, params)
    return {"series": [{"store_name": r["store_name"], "revenue": float(r["revenue"] or 0)} for r in rows]}


def top_customers(limit, date_from, date_to):
    where, params = _range_where(date_from, date_to)
    sql = (
        f"SELECT c.full_name, SUM(oi.quantity * oi.unit_price) AS spend "
        f"FROM orders o JOIN order_items oi ON oi.order_id = o.order_id "
        f"JOIN customers c ON c.customer_id = o.customer_id WHERE 1=1 {where} "
        f"GROUP BY c.full_name ORDER BY spend DESC FETCH FIRST {int(limit)} ROWS ONLY"
    )
    rows = _q(co_pool(), sql, params)
    return {"series": [{"full_name": r["full_name"], "spend": float(r["spend"] or 0)} for r in rows]}


def headcount_by_dept():
    sql = (
        "SELECT d.department_name, COUNT(e.employee_id) AS cnt "
        "FROM departments d LEFT JOIN employees e ON e.department_id = d.department_id "
        "GROUP BY d.department_name ORDER BY cnt DESC"
    )
    rows = _q(hr_pool(), sql)
    return {"series": [{"department_name": r["department_name"], "cnt": r["cnt"]} for r in rows]}


def salary_stats():
    by_job = _q(
        hr_pool(),
        "SELECT job_title, ROUND(AVG(salary),2) AS avg_sal, "
        "MIN(salary) AS min_sal, MAX(salary) AS max_sal "
        "FROM employees e JOIN jobs j ON j.job_id = e.job_id "
        "GROUP BY job_title ORDER BY avg_sal DESC",
    )
    by_dept = _q(
        hr_pool(),
        "SELECT d.department_name, ROUND(AVG(e.salary),2) AS avg_sal "
        "FROM employees e JOIN departments d ON d.department_id = e.department_id "
        "GROUP BY d.department_name ORDER BY avg_sal DESC",
    )
    dist = _q(
        hr_pool(),
        "SELECT (FLOOR(salary/10000)*10000) AS bucket, COUNT(*) AS cnt "
        "FROM employees GROUP BY FLOOR(salary/10000) ORDER BY bucket",
    )
    return {
        "by_job": by_job,
        "by_department": by_dept,
        "distribution": [{"bucket": r["bucket"], "cnt": r["cnt"]} for r in dist],
    }


def hires_over_time():
    sql = (
        "SELECT TRUNC(hire_date, 'YYYY') AS year, COUNT(*) AS cnt "
        "FROM employees GROUP BY TRUNC(hire_date, 'YYYY') ORDER BY year"
    )
    rows = _q(hr_pool(), sql)
    return {"points": [{"year": r["year"].isoformat() if r["year"] else None, "cnt": r["cnt"]} for r in rows]}
