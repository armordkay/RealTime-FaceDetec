from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_current_user
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.common import build_success
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])
service = AuthService()


@router.post("/login")
def login(payload: LoginRequest):
    data = service.login(
        username=payload.username,
        password=payload.password,
        requested_role=payload.requested_role,
    )
    return build_success(data)


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    data = service.get_me(current_user["id"])
    return build_success(data)


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    data = service.change_password(
        user_id=current_user["id"],
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return build_success(data)
