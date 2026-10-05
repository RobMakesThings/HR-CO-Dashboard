from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderLine(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class OrderBase(BaseModel):
    customer_id: int
    store_id: int
    order_status: str = Field(min_length=1, max_length=10)
    order_tms: datetime
    items: list[OrderLine] = Field(default_factory=list, max_length=50)


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_id: int | None = None
    store_id: int | None = None
    order_status: str | None = Field(default=None, max_length=10)
    order_tms: datetime | None = None
    items: list[OrderLine] | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    order_id: int
    order_tms: datetime
    customer_id: int
    customer_name: str | None = None
    order_status: str
    store_id: int
    store_name: str | None = None
    total: float | None = None
    item_count: int | None = None


class OrderDetail(OrderOut):
    items: list[dict] = []
