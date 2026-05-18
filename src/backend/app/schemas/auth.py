from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)
    requested_role: str | None = Field(default=None)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=6)
    new_password: str = Field(min_length=6)


class UserMe(BaseModel):
    id: int
    username: str
    email: str
    role: str
    employee_id: int | None


class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserMe
