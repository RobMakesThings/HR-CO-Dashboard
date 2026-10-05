from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class EmployeeBase(BaseModel):
    first_name: str | None = Field(default=None, max_length=20)
    last_name: str = Field(min_length=1, max_length=25)
    # HR stores emails as plain usernames (e.g. 'EABEL'), so keep as str not EmailStr.
    email: str = Field(min_length=1, max_length=25)
    phone_number: str | None = Field(default=None, max_length=20)
    hire_date: date
    job_id: str = Field(min_length=1, max_length=10)
    salary: float | None = Field(default=None, ge=0)
    commission_pct: float | None = Field(default=None, ge=0, le=1)
    manager_id: int | None = None
    department_id: int | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=20)
    last_name: str | None = Field(default=None, min_length=1, max_length=25)
    email: str | None = Field(default=None, min_length=1, max_length=25)
    phone_number: str | None = Field(default=None, max_length=20)
    hire_date: date | None = None
    job_id: str | None = Field(default=None, max_length=10)
    salary: float | None = Field(default=None, ge=0)
    commission_pct: float | None = Field(default=None, ge=0, le=1)
    manager_id: int | None = None
    department_id: int | None = None


class EmployeeOut(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    job_title: str | None = None
    department_name: str | None = None
    manager_name: str | None = None
