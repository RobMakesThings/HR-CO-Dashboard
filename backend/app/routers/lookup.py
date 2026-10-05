from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..repositories import lookup as repo

router = APIRouter(
    prefix="/lookup",
    tags=["lookup"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/departments")
def departments():
    return repo.departments()


@router.get("/jobs")
def jobs():
    return repo.jobs()


@router.get("/managers")
def managers():
    return repo.managers()


@router.get("/locations")
def locations():
    return repo.locations()


@router.get("/countries")
def countries():
    return repo.countries()


@router.get("/regions")
def regions():
    return repo.regions()


@router.get("/stores")
def stores():
    return repo.stores()


@router.get("/order-statuses")
def order_statuses():
    return repo.order_statuses()


@router.get("/products")
def products():
    return repo.products_compact()


@router.get("/customers")
def customers():
    return repo.customers_compact()
