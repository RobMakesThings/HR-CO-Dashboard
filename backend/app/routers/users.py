from fastapi import APIRouter, Depends, HTTPException

from ..deps import require_role
from ..repositories import users as repo
from ..schemas.auth import UserCreate, UserOut, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=list[UserOut])
def list_users():
    return repo.list_users()


@router.post("", response_model=UserOut, status_code=201)
def create_user(body: UserCreate):
    if repo.find_by_username(body.username):
        raise HTTPException(409, "Username already exists")
    return repo.create_user(body)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate):
    if repo.get_user(user_id) is None:
        raise HTTPException(404, "User not found")
    return repo.update_user(user_id, body)


@router.delete("/{user_id}")
def delete_user(user_id: int):
    if repo.get_user(user_id) is None:
        raise HTTPException(404, "User not found")
    repo.delete_user(user_id)
    return {"deleted": True}
