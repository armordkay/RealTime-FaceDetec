from sqlalchemy import select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import LeaveCalendar


class LeaveCalendarRepository:
    def create(self, item: LeaveCalendar) -> LeaveCalendar:
        if supabase_enabled():
            rows = get_supabase_client().insert("leave_calendar", model_to_payload(item, "leave_calendar"))
            return row_to_model(LeaveCalendar, rows[0], "leave_calendar")

        with session_scope() as db:
            db.add(item)
            db.flush()
            db.refresh(item)
            return item

    def find_for_employee_date(self, employee_id: int, leave_date: str) -> LeaveCalendar | None:
        records = self.list_by_date(leave_date)
        for item in records:
            if item.status == "approved" and (item.employee_id is None or item.employee_id == employee_id):
                return item
        return None

    def list_by_date(self, leave_date: str) -> list[LeaveCalendar]:
        if supabase_enabled():
            rows = get_supabase_client().select(
                "leave_calendar",
                {"leave_date": f"eq.{leave_date}", "order": "id.asc"},
            )
            return [row_to_model(LeaveCalendar, row, "leave_calendar") for row in rows]

        with session_scope() as db:
            statement = select(LeaveCalendar).where(LeaveCalendar.leave_date == leave_date).order_by(LeaveCalendar.id)
            return list(db.scalars(statement))
