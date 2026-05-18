from pydantic import BaseModel, Field


class EmployeeCreateRequest(BaseModel):
    employee_code: str = Field(min_length=2, max_length=50)
    full_name: str = Field(min_length=2, max_length=200)
    email: str
    phone: str = Field(default="")
    department: str = Field(min_length=1, max_length=100)
    position: str = Field(default="")
    default_shift_id: int | None = None


class EmployeeUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: str | None = None
    phone: str | None = None
    department: str | None = Field(default=None, min_length=1, max_length=100)
    position: str | None = None
    status: str | None = None
    default_shift_id: int | None = None


class EmployeeSelfUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    email: str | None = None
    phone: str | None = None


class EmployeeItem(BaseModel):
    id: int
    employee_code: str
    full_name: str
    email: str
    phone: str
    department: str
    position: str
    status: str
    default_shift_id: int | None
    enrolled_samples: int
    created_at: str
    updated_at: str
