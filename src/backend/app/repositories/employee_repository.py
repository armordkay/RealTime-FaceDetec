from sqlalchemy import select

from app.db.session import session_scope
from app.models.entities import Employee, utc_now


class EmployeeRepository:
    def list(self, search: str | None = None, department: str | None = None, status: str | None = None) -> list[Employee]:
        with session_scope() as db:
            records = list(db.scalars(select(Employee).order_by(Employee.id)))

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
        with session_scope() as db:
            db.add(employee)
            db.flush()
            db.refresh(employee)
            return employee

    def get(self, employee_id: int) -> Employee | None:
        with session_scope() as db:
            return db.get(Employee, employee_id)

    def update(self, employee: Employee) -> Employee:
        employee.updated_at = utc_now()
        with session_scope() as db:
            merged = db.merge(employee)
            db.flush()
            db.refresh(merged)
            return merged

    def exists_by_code(self, employee_code: str, ignore_id: int | None = None) -> bool:
        lookup = employee_code.strip().lower()
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
