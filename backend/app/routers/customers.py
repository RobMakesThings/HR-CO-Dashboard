from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_current_user, require_role
from ..repositories import customers as repo
from ..schemas.common import Page
from ..schemas.customers import CustomerCreate, CustomerOut, CustomerUpdate
from ..seeding import customers as seed
from ..db import co_pool

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerOut])
def list_customers(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    search: str | None = None,
    _u: dict = Depends(get_current_user),
):
    return repo.list_customers(page, pageSize, search)


@router.get("/generate", response_model=CustomerCreate)
def generate(_u: dict = Depends(require_role("admin"))):
    return seed.generate_customer()


@router.post("/bulk", status_code=201)
def bulk(
    count: int = Query(5, ge=1, le=1000),
    _u: dict = Depends(require_role("admin")),
):
    inserted = 0
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        for _ in range(count):
            g = seed.generate_customer()
            cur.execute(
                "INSERT INTO customers (email_address, full_name) VALUES (:1, :2)",
                (g["email_address"], g["full_name"]),
            )
            inserted += 1
        conn.commit()
    return {"inserted": inserted}


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, _u: dict = Depends(get_current_user)):
    row = repo.get_customer(customer_id)
    if row is None:
        raise HTTPException(404, "Customer not found")
    return row


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(body: CustomerCreate, _u: dict = Depends(require_role("admin"))):
    return repo.create_customer(body)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int, body: CustomerUpdate, _u: dict = Depends(require_role("admin"))
):
    if repo.get_customer(customer_id) is None:
        raise HTTPException(404, "Customer not found")
    return repo.update_customer(customer_id, body)


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, _u: dict = Depends(require_role("admin"))):
    if not repo.delete_customer(customer_id):
        raise HTTPException(404, "Customer not found")
    return {"deleted": True}
