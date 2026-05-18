from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import DailyAttendanceEmailNotification


class DailyAttendanceEmailNotificationRepository:
    def get_by_employee_date(
        self,
        employee_id: int,
        work_date: str,
    ) -> DailyAttendanceEmailNotification | None:
        if supabase_enabled():
            rows = get_supabase_client().select(
                "daily_attendance_email_notifications",
                {
                    "employee_id": f"eq.{employee_id}",
                    "work_date": f"eq.{work_date}",
                    "limit": "1",
                },
            )
            return row_to_model(DailyAttendanceEmailNotification, rows[0], "daily_attendance_email_notifications") if rows else None

        with session_scope() as db:
            return (
                db.query(DailyAttendanceEmailNotification)
                .filter(DailyAttendanceEmailNotification.employee_id == employee_id)
                .filter(DailyAttendanceEmailNotification.work_date == work_date)
                .first()
            )

    def create(self, item: DailyAttendanceEmailNotification) -> DailyAttendanceEmailNotification:
        if supabase_enabled():
            rows = get_supabase_client().insert(
                "daily_attendance_email_notifications",
                model_to_payload(item, "daily_attendance_email_notifications"),
            )
            return row_to_model(DailyAttendanceEmailNotification, rows[0], "daily_attendance_email_notifications")

        with session_scope() as db:
            db.add(item)
            db.flush()
            db.refresh(item)
            return item
