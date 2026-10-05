from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    email_address: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    email_address: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    customer_id: int
    email_address: str
    full_name: str
