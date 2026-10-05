from fastapi import APIRouter, Depends, HTTPException, Query

from ..db import co_pool
from ..deps import get_current_user, require_role
from ..repositories import products as repo
from ..schemas.common import Page
from ..schemas.products import ProductCreate, ProductOut, ProductUpdate
from ..seeding import products as seed

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=Page[ProductOut])
def list_products(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200),
    search: str | None = None,
    _u: dict = Depends(get_current_user),
):
    return repo.list_products(page, pageSize, search)


@router.get("/generate", response_model=ProductCreate)
def generate(_u: dict = Depends(require_role("admin"))):
    return seed.generate_product()


@router.post("/bulk", status_code=201)
def bulk(count: int = Query(5, ge=1, le=1000), _u: dict = Depends(require_role("admin"))):
    inserted = 0
    with co_pool().acquire() as conn:
        cur = conn.cursor()
        for _ in range(count):
            g = seed.generate_product()
            cur.execute(
                "INSERT INTO products (product_name, unit_price) VALUES (:1, :2)",
                (g["product_name"], g["unit_price"]),
            )
            inserted += 1
        conn.commit()
    return {"inserted": inserted}


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, _u: dict = Depends(get_current_user)):
    row = repo.get_product(product_id)
    if row is None:
        raise HTTPException(404, "Product not found")
    return row


@router.post("", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, _u: dict = Depends(require_role("admin"))):
    return repo.create_product(body)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int, body: ProductUpdate, _u: dict = Depends(require_role("admin"))
):
    if repo.get_product(product_id) is None:
        raise HTTPException(404, "Product not found")
    return repo.update_product(product_id, body)


@router.delete("/{product_id}")
def delete_product(product_id: int, _u: dict = Depends(require_role("admin"))):
    if not repo.delete_product(product_id):
        raise HTTPException(404, "Product not found")
    return {"deleted": True}
