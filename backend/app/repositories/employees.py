import oracledb

from ..db import hr_pool
from ..errors import ClientError
from ..schemas.employees import EmployeeCreate, EmployeeUpdate

_JOINS = (
    "FROM employees e "
    "LEFT JOIN jobs j ON j.job_id = e.job_id "
    "LEFT JOIN employees m ON m.employee_id = e.manager_id "
    "LEFT JOIN departments d ON d.department_id = e.department_id"
)

_COLS = (
    "SELECT e.employee_id, e.first_name, e.last_name, e.email, e.phone_number, "
    "e.hire_date, e.job_id, j.job_title, e.salary, e.commission_pct, "
    "e.manager_id, m.first_name || ' ' || m.last_name AS manager_name, "
    "e.department_id, d.department_name "
)

_KEYS = [
    "employee_id", "first_name", "last_name", "email", "phone_number", "hire_date",
    "job_id", "job_title", "salary", "commission_pct", "manager_id",
    "manager_name", "department_id", "department_name",
]


def _row(r):
    return dict(zip(_KEYS, r))


def _where(department_id=None, job_id=None, search=None):
    where, params = [], ()
    if department_id:
        where.append("e.department_id = :" + str(len(params) + 1))
        params += (department_id,)
    if job_id:
        where.append("e.job_id = :" + str(len(params) + 1))
        params += (job_id,)
    if search:
        where.append(
            "(LOWER(e.first_name) LIKE :" + str(len(params) + 1)
            + " OR LOWER(e.last_name) LIKE :" + str(len(params) + 1) + ")"
        )
        params += (f"%{search.lower()}%",)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    return where_sql, params


def list_employees(page=1, page_size=20, department_id=None, job_id=None, search=None):
    where_sql, params = _where(department_id, job_id, search)
    page, page_size = max(1, page), min(200, max(1, page_size))
    offset = (page - 1) * page_size
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        cc = conn.cursor()
        cc.execute(
            f"SELECT COUNT(*) FROM employees e {where_sql}",
            params,
        )
        total = cc.fetchone()[0]
        cur.execute(
            f"{_COLS} {_JOINS} {where_sql} "
            f"ORDER BY e.last_name, e.first_name "
            f"OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY",
            params,
        )
        items = [_row(r) for r in cur.fetchall()]
        return {"items": items, "total": total, "page": page, "pageSize": page_size}


def get_employee(employee_id: int):
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        cur.execute(f"{_COLS} {_JOINS} WHERE e.employee_id = :1", (employee_id,))
        r = cur.fetchone()
        return _row(r) if r else None


def _map_error(exc):
    msg = str(exc)
    if "ORA-00001" in msg:
        raise ClientError(409, "DUP_EMAIL", "That employee email already exists")
    if "ORA-02291" in msg:
        raise ClientError(
            409, "FK_VIOLATION", "References a job, department, or manager that doesn't exist"
        )
    raise ClientError(400, "DB_ERROR", msg)


def create_employee(data: EmployeeCreate):
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT employees_seq.NEXTVAL FROM dual")
            eid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO employees (employee_id, first_name, last_name, email, "
                "phone_number, hire_date, job_id, salary, commission_pct, "
                "manager_id, department_id) "
                "VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11)",
                (eid, data.first_name, data.last_name, data.email, data.phone_number,
                 data.hire_date, data.job_id, data.salary, data.commission_pct,
                 data.manager_id, data.department_id),
            )
            conn.commit()
            return get_employee(eid)
        except Exception as exc:
            conn.rollback()
            _map_error(exc)


def update_employee(employee_id: int, data: EmployeeUpdate):
    fields = {}
    for k in ["first_name", "last_name", "email", "phone_number", "hire_date",
              "job_id", "salary", "commission_pct", "manager_id", "department_id"]:
        v = getattr(data, k)
        if v is not None:
            fields[k] = v
    if fields:
        sets = ", ".join(f"{k} = :{i+1}" for i, k in enumerate(fields))
        binds = list(fields.values()) + [employee_id]
        with hr_pool().acquire() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"UPDATE employees SET {sets} WHERE employee_id = :{len(binds)}",
                    binds,
                )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                _map_error(exc)
    return get_employee(employee_id)


def delete_employee(employee_id: int) -> bool:
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM employees WHERE employee_id = :1", (employee_id,))
            conn.commit()
            return cur.rowcount > 0
        except Exception as exc:
            conn.rollback()
            raise ClientError(409, "FK_VIOLATION", "Employee is referenced by other records")
