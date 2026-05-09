from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import require_roles
from app.core.permissions import ROLE_ADMIN
from app.schemas.admin import AdminUserCreateRequest, AdminUserUpdateRequest, SystemConfigUpdateRequest
from app.schemas.common import build_success
from app.services.admin_service import AdminService


router = APIRouter(prefix="/admin", tags=["admin"])
service = AdminService()


@router.get("/overview")
def overview(_: dict = Depends(require_roles(ROLE_ADMIN))):
    return build_success(service.overview())


@router.get("/access-logs")
def access_logs(limit: int = Query(default=50, ge=1, le=200), _: dict = Depends(require_roles(ROLE_ADMIN))):
    return build_success(service.recent_access_logs(limit=limit))


@router.get("/users")
def list_users(_: dict = Depends(require_roles(ROLE_ADMIN))):
    return build_success(service.list_users())


@router.post("/users")
def create_user(payload: AdminUserCreateRequest, _: dict = Depends(require_roles(ROLE_ADMIN))):
    return build_success(service.create_user(payload.model_dump()))


@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: AdminUserUpdateRequest, _: dict = Depends(require_roles(ROLE_ADMIN))):
    return build_success(service.update_user(user_id, payload.model_dump(exclude_unset=True)))


@router.get("/config")
def get_config(_: dict = Depends(require_roles(ROLE_ADMIN))):
    return build_success(service.get_config())


@router.patch("/config")
def update_config(payload: SystemConfigUpdateRequest, _: dict = Depends(require_roles(ROLE_ADMIN))):
    return build_success(service.update_config(payload.model_dump()))
