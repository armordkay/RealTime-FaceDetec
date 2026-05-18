from datetime import date

from fastapi import HTTPException, status

from app.core.timezone import to_vietnam_iso
from app.models.entities import LeaveCalendar, utc_now
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.leave_calendar_repository import LeaveCalendarRepository


class LeaveCalendarService:
    def __init__(self) -> None:
        self.leave_repository = LeaveCalendarRepository()
        self.employee_repository = EmployeeRepository()

    def create(self, payload: dict, actor_user: dict) -> dict:
        leave_date = self._parse_date(payload["leave_date"])
        employee_id = payload.get("employee_id")
        if employee_id is not None and self.employee_repository.get(employee_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee not found")

        item = LeaveCalendar(
            employee_id=employee_id,
            leave_date=leave_date.isoformat(),
            leave_type=payload.get("leave_type") or "leave",
            reason=payload.get("reason") or "",
            status="approved",
            created_by_user_id=actor_user.get("id"),
            created_at=utc_now(),
        )
        return self._to_item(self.leave_repository.create(item))

    def list_by_date(self, leave_date: str) -> list[dict]:
        parsed = self._parse_date(leave_date)
        return [self._to_item(item) for item in self.leave_repository.list_by_date(parsed.isoformat())]

    def _parse_date(self, value: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid leave_date") from exc

    def _to_item(self, item: LeaveCalendar) -> dict:
        return {
            "id": item.id,
            "employee_id": item.employee_id,
            "leave_date": item.leave_date,
            "leave_type": item.leave_type,
            "reason": item.reason,
            "status": item.status,
            "created_by_user_id": item.created_by_user_id,
            "created_at": to_vietnam_iso(item.created_at),
        }
