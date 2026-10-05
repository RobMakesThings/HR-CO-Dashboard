from fastapi import APIRouter, HTTPException, status

from ..repositories.users import find_by_username
from ..schemas.auth import LoginRequest, TokenResponse
from ..security import create_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = find_by_username(body.username)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    token = create_token(user["app_user_id"], user["username"], user["role"])
    return TokenResponse(
        access_token=token, role=user["role"], username=user["username"]
    )
