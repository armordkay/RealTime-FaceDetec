from __future__ import annotations

from sqlalchemy import select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import Employee, utc_now


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
