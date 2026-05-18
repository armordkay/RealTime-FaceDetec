from fastapi import HTTPException, status

from app.core.timezone import to_vietnam_iso
from app.models.entities import Employee, utc_now
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.face_repository import FaceRepository
from app.repositories.shift_repository import ShiftRepository
from app.schemas.common import build_pagination


class EmployeeService:
    def __init__(self) -> None:
        self.employee_repository = EmployeeRepository()
        self.shift_repository = ShiftRepository()
        self.face_repository = FaceRepository()

    def list(
        self,
        page: int,
        page_size: int,
        search: str | None,
        department: str | None,
        status_value: str | None,
    ) -> dict:
        records = self.employee_repository.list(
            search=search,
            department=department,
            status=status_value,
        )
        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        page_records = records[start:end]
        sample_counts = self.face_repository.count_by_employee_ids([record.id for record in page_records])
        items = [self._to_item(record, sample_counts.get(record.id, 0)) for record in page_records]
        return {
            "items": items,
            "pagination": build_pagination(page, page_size, total),
        }

    def create(self, payload: dict) -> dict:
        if self.employee_repository.exists_by_code(payload["employee_code"]):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee code already exists")

        shift_id = payload.get("default_shift_id")
        if shift_id is not None and self.shift_repository.get(shift_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shift not found")

        employee = Employee(
            employee_code=payload["employee_code"],
            full_name=payload["full_name"],
            email=payload["email"],
            phone=payload.get("phone", ""),
            department=payload["department"],
            position=payload.get("position", ""),
            status="active",
            default_shift_id=payload.get("default_shift_id"),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.employee_repository.create(employee)
        return self._to_item(employee)

    def get_by_id(self, employee_id: int) -> dict:
        employee = self.employee_repository.get(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return self._to_item(employee)

    def update(self, employee_id: int, payload: dict) -> dict:
        employee = self.employee_repository.get(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        new_shift_id = payload.get("default_shift_id")
        if new_shift_id is not None and self.shift_repository.get(new_shift_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Shift not found")

        for field in ["full_name", "email", "phone", "department", "position", "status", "default_shift_id"]:
            if field in payload and payload[field] is not None:
                setattr(employee, field, payload[field])

        self.employee_repository.update(employee)
        return self._to_item(employee)

    def deactivate(self, employee_id: int) -> dict:
        employee = self.employee_repository.deactivate(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return self._to_item(employee)

    def hard_delete(self, employee_id: int) -> dict:
        employee = self.employee_repository.get(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        dependency_counts = self.employee_repository.dependency_counts(employee_id)
        blockers = {key: value for key, value in dependency_counts.items() if value > 0}
        if blockers:
            details = ", ".join(f"{key}={value}" for key, value in blockers.items())
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot hard delete employee with related records: {details}. Deactivate instead.",
            )

        deleted = self.employee_repository.hard_delete(employee_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        return {
            "deleted": True,
            "employee_id": employee_id,
            "message": "Employee permanently deleted",
        }

    def get_my_profile(self, current_user: dict) -> dict:
        employee_id = current_user.get("employee_id")
        if employee_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked employee profile")

        employee = self.employee_repository.get(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        return self._to_item(employee)

    def update_my_profile(self, current_user: dict, payload: dict) -> dict:
        employee_id = current_user.get("employee_id")
        if employee_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked employee profile")

        employee = self.employee_repository.get(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        for field in ["full_name", "email", "phone"]:
            if field in payload and payload[field] is not None:
                setattr(employee, field, payload[field])

        self.employee_repository.update(employee)
        return self._to_item(employee)

    def _to_item(self, employee: Employee, enrolled_samples: int | None = None) -> dict:
        return {
            "id": employee.id,
            "employee_code": employee.employee_code,
            "full_name": employee.full_name,
            "email": employee.email,
            "phone": employee.phone,
            "department": employee.department,
            "position": employee.position,
            "status": employee.status,
            "default_shift_id": employee.default_shift_id,
            "enrolled_samples": enrolled_samples
            if enrolled_samples is not None
            else self.face_repository.count_by_employee(employee.id),
            "created_at": to_vietnam_iso(employee.created_at),
            "updated_at": to_vietnam_iso(employee.updated_at),
        }
