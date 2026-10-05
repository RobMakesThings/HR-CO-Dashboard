from datetime import date, timedelta

from faker import Faker

from ..db import hr_pool

_fake = Faker()


def _lookups():
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute("SELECT job_id, min_salary, max_salary FROM jobs")
        jobs = cur.fetchall()
        cur.execute("SELECT department_id FROM departments")
        depts = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT employee_id FROM employees")
        mgrs = [r[0] for r in cur.fetchall()]
    return jobs, depts, mgrs


def generate_employee() -> dict:
    jobs, depts, mgrs = _lookups()
    if jobs:
        job_id, lo, hi = _fake.random.choice(jobs)
    else:
        job_id, lo, hi = "SA_REP", 6100, 8400
    lo = lo or 2000
    hi = hi or 20000
    first = _fake.first_name()
    last = _fake.last_name()
    base = _fake.user_name().replace(".", "")
    email = f"{base[:8]}{_fake.random_int(0, 999)}@example.com"
    return {
        "first_name": first,
        "last_name": last,
        "email": email,
        "phone_number": _fake.phone_number()[:20],
        "hire_date": date.today() - timedelta(days=_fake.random_int(30, 7000)),
        "job_id": job_id,
        "salary": round(_fake.random.uniform(lo, hi), 2),
        "commission_pct": 0.25 if "SA" in job_id else None,
        "manager_id": _fake.random.choice(mgrs) if mgrs else None,
        "department_id": _fake.random.choice(depts) if depts else None,
    }
