from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import require_roles
from app.core.permissions import ROLE_ADMIN, ROLE_MANAGER
from app.schemas.common import build_success
from app.schemas.employee import EmployeeCreateRequest, EmployeeSelfUpdateRequest, EmployeeUpdateRequest
from app.services.employee_service import EmployeeService


router = APIRouter(prefix="/employees", tags=["employees"])
service = EmployeeService()


@router.get("")
def list_employees(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    department: str | None = None,
    status: str | None = None,
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = service.list(
        page=page,
        page_size=page_size,
        search=search,
        department=department,
        status_value=status,
    )
    return build_success(data)


@router.post("")
def create_employee(
    payload: EmployeeCreateRequest,
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = service.create(payload.model_dump())
    return build_success(data)


@router.get("/me")
def get_my_profile(current_user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    data = service.get_my_profile(current_user)
    return build_success(data)


@router.patch("/me")
def update_my_profile(
    payload: EmployeeSelfUpdateRequest,
    current_user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = service.update_my_profile(current_user=current_user, payload=payload.model_dump(exclude_unset=True))
    return build_success(data)


@router.get("/{employee_id}")
def get_employee(employee_id: int, _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    data = service.get_by_id(employee_id)
    return build_success(data)


@router.patch("/{employee_id}")
def update_employee(
    employee_id: int,
    payload: EmployeeUpdateRequest,
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = service.update(employee_id, payload.model_dump(exclude_unset=True))
    return build_success(data)


@router.delete("/{employee_id}")
def deactivate_employee(employee_id: int, _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    data = service.deactivate(employee_id)
    return build_success(data)


@router.delete("/{employee_id}/hard-delete")
def hard_delete_employee(employee_id: int, _: dict = Depends(require_roles(ROLE_ADMIN))):
    data = service.hard_delete(employee_id)
    return build_success(data)
