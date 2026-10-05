from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import hr_pool
from ..deps import get_current_user, require_role
from ..repositories import employees as repo
from ..schemas.common import Page
from ..schemas.employees import EmployeeCreate, EmployeeOut, EmployeeUpdate
from ..seeding import employees as seed

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=Page[EmployeeOut])
def list_employees(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    department_id: int | None = None,
    job_id: str | None = None,
    search: str | None = None,
    _u: dict = Depends(get_current_user),
):
    return repo.list_employees(page, pageSize, department_id, job_id, search)


@router.get("/generate", response_model=EmployeeCreate)
def generate(_u: dict = Depends(require_role("admin"))):
    return seed.generate_employee()


@router.post("/bulk", status_code=201)
def bulk(count: int = Query(5, ge=1, le=1000), _u: dict = Depends(require_role("admin"))):
    inserted = 0
    with hr_pool().acquire() as conn:
        cur = conn.cursor()
        for _ in range(count):
            g = seed.generate_employee()
            cur.execute("SELECT employees_seq.NEXTVAL FROM dual")
            eid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO employees (employee_id, first_name, last_name, email, "
                "phone_number, hire_date, job_id, salary, commission_pct, "
                "manager_id, department_id) VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11)",
                (eid, g["first_name"], g["last_name"], g["email"], g["phone_number"],
                 g["hire_date"], g["job_id"], g["salary"], g["commission_pct"],
                 g["manager_id"], g["department_id"]),
            )
            inserted += 1
        conn.commit()
    return {"inserted": inserted}


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, _u: dict = Depends(get_current_user)):
    row = repo.get_employee(employee_id)
    if row is None:
        raise HTTPException(404, "Employee not found")
    return row


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(body: EmployeeCreate, _u: dict = Depends(require_role("admin"))):
    return repo.create_employee(body)


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int, body: EmployeeUpdate, _u: dict = Depends(require_role("admin"))
):
    if repo.get_employee(employee_id) is None:
        raise HTTPException(404, "Employee not found")
    return repo.update_employee(employee_id, body)


@router.delete("/{employee_id}")
def delete_employee(employee_id: int, _u: dict = Depends(require_role("admin"))):
    if not repo.delete_employee(employee_id):
        raise HTTPException(404, "Employee not found")
    return {"deleted": True}
