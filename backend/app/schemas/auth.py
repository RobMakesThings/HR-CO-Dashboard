from pydantic import BaseModel, Field, ConfigDict


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(pattern="^(admin|viewer)$")


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: str | None = Field(default=None, pattern="^(admin|viewer)$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    app_user_id: int
    username: str
    role: str
    created_at: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
