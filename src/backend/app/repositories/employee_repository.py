from __future__ import annotations

from sqlalchemy import func, select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import (
    AnomalyFlag,
    AttendanceEmailNotification,
    AttendanceLog,
    DailyAttendanceEmailNotification,
    Employee,
    FaceSample,
    LeaveCalendar,
    User,
    utc_now,
)


class EmployeeRepository:
    def list(self, search: str | None = None, department: str | None = None, status: str | None = None) -> list[Employee]:
        if supabase_enabled():
            records = [
                row_to_model(Employee, row, "employees")
                for row in get_supabase_client().select("employees", {"order": "id.asc"})
            ]
            return self._filter(records, search, department, status)

        with session_scope() as db:
            records = list(db.scalars(select(Employee).order_by(Employee.id)))
            return self._filter(records, search, department, status)

    def _filter(
        self,
        records: list[Employee],
        search: str | None,
        department: str | None,
        status: str | None,
    ) -> list[Employee]:
        if search:
            query = search.strip().lower()
            records = [
                item
                for item in records
                if query in item.full_name.lower()
                or query in item.employee_code.lower()
                or query in item.email.lower()
            ]
        if department:
            records = [item for item in records if item.department.lower() == department.strip().lower()]
        if status:
            records = [item for item in records if item.status.lower() == status.strip().lower()]
        return records

    def create(self, employee: Employee) -> Employee:
        if supabase_enabled():
            rows = get_supabase_client().insert("employees", model_to_payload(employee, "employees"))
            return row_to_model(Employee, rows[0], "employees")

        with session_scope() as db:
            db.add(employee)
            db.flush()
            db.refresh(employee)
            return employee

    def get(self, employee_id: int) -> Employee | None:
        if supabase_enabled():
            rows = get_supabase_client().select("employees", {"id": f"eq.{employee_id}", "limit": "1"})
            return row_to_model(Employee, rows[0], "employees") if rows else None

        with session_scope() as db:
            return db.get(Employee, employee_id)

    def list_by_ids(self, employee_ids: list[int]) -> list[Employee]:
        if not employee_ids:
            return []

        unique_ids = list(dict.fromkeys(employee_ids))
        if supabase_enabled():
            return [employee for employee in self.list() if employee.id in set(unique_ids)]

        with session_scope() as db:
            statement = select(Employee).where(Employee.id.in_(unique_ids)).order_by(Employee.id)
            return list(db.scalars(statement))

    def update(self, employee: Employee) -> Employee:
        employee.updated_at = utc_now()
        if supabase_enabled():
            rows = get_supabase_client().update(
                "employees",
                {"id": f"eq.{employee.id}"},
                model_to_payload(employee, "employees"),
            )
            return row_to_model(Employee, rows[0], "employees")

        with session_scope() as db:
            merged = db.merge(employee)
            db.flush()
            db.refresh(merged)
            return merged

    def exists_by_code(self, employee_code: str, ignore_id: int | None = None) -> bool:
        lookup = employee_code.strip().lower()
        if supabase_enabled():
            records = self.list()
            for item in records:
                if ignore_id is not None and item.id == ignore_id:
                    continue
                if item.employee_code.lower() == lookup:
                    return True
            return False

        with session_scope() as db:
            records = db.scalars(select(Employee)).all()
            for item in records:
                if ignore_id is not None and item.id == ignore_id:
                    continue
                if item.employee_code.lower() == lookup:
                    return True
            return False

    def deactivate(self, employee_id: int) -> Employee | None:
        employee = self.get(employee_id)
        if employee is None:
            return None
        employee.status = "inactive"
        return self.update(employee)

    def dependency_counts(self, employee_id: int) -> dict[str, int]:
        if supabase_enabled():
            return {
                "attendance_logs": len(get_supabase_client().select("attendance_logs", {"employee_id": f"eq.{employee_id}"})),
                "face_samples": len(get_supabase_client().select("face_samples", {"employee_id": f"eq.{employee_id}"})),
                "users": len(get_supabase_client().select("users", {"employee_id": f"eq.{employee_id}"})),
                "anomaly_flags": len(get_supabase_client().select("anomaly_flags", {"employee_id": f"eq.{employee_id}"})),
                "attendance_email_notifications": len(get_supabase_client().select("attendance_email_notifications", {"employee_id": f"eq.{employee_id}"})),
                "daily_attendance_email_notifications": len(get_supabase_client().select("daily_attendance_email_notifications", {"employee_id": f"eq.{employee_id}"})),
                "leave_calendar": len(get_supabase_client().select("leave_calendar", {"employee_id": f"eq.{employee_id}"})),
            }

        with session_scope() as db:
            def count(model) -> int:
                return int(db.scalar(select(func.count()).select_from(model).where(model.employee_id == employee_id)) or 0)

            return {
                "attendance_logs": count(AttendanceLog),
                "face_samples": count(FaceSample),
                "users": count(User),
                "anomaly_flags": count(AnomalyFlag),
                "attendance_email_notifications": count(AttendanceEmailNotification),
                "daily_attendance_email_notifications": count(DailyAttendanceEmailNotification),
                "leave_calendar": count(LeaveCalendar),
            }

    def hard_delete(self, employee_id: int) -> bool:
        if supabase_enabled():
            return get_supabase_client().delete("employees", {"id": f"eq.{employee_id}"})

        with session_scope() as db:
            employee = db.get(Employee, employee_id)
            if employee is None:
                return False
            db.delete(employee)
            return True
