from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import AttendanceEmailNotification


class AttendanceEmailNotificationRepository:
    def get_by_log_id(self, attendance_log_id: int) -> AttendanceEmailNotification | None:
        if supabase_enabled():
            rows = get_supabase_client().select(
                "attendance_email_notifications",
                {"attendance_log_id": f"eq.{attendance_log_id}", "limit": "1"},
            )
            return row_to_model(AttendanceEmailNotification, rows[0], "attendance_email_notifications") if rows else None

        with session_scope() as db:
            return (
                db.query(AttendanceEmailNotification)
                .filter(AttendanceEmailNotification.attendance_log_id == attendance_log_id)
                .first()
            )

    def create(self, item: AttendanceEmailNotification) -> AttendanceEmailNotification:
        if supabase_enabled():
            rows = get_supabase_client().insert(
                "attendance_email_notifications",
                model_to_payload(item, "attendance_email_notifications"),
            )
            return row_to_model(AttendanceEmailNotification, rows[0], "attendance_email_notifications")

        with session_scope() as db:
            db.add(item)
            db.flush()
            db.refresh(item)
            return item
