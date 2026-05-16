from sqlalchemy import select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import AttendanceAuditLog


class AttendanceAuditRepository:
    def create(self, audit_log: AttendanceAuditLog) -> AttendanceAuditLog:
        if supabase_enabled():
            rows = get_supabase_client().insert(
                "attendance_audit_logs",
                model_to_payload(audit_log, "attendance_audit_logs"),
            )
            return row_to_model(AttendanceAuditLog, rows[0], "attendance_audit_logs")

        with session_scope() as db:
            db.add(audit_log)
            db.flush()
            db.refresh(audit_log)
            return audit_log

    def list_by_log(self, attendance_log_id: int) -> list[AttendanceAuditLog]:
        if supabase_enabled():
            rows = get_supabase_client().select(
                "attendance_audit_logs",
                {
                    "attendance_log_id": f"eq.{attendance_log_id}",
                    "order": "created_at.desc",
                },
            )
            return [row_to_model(AttendanceAuditLog, row, "attendance_audit_logs") for row in rows]

        with session_scope() as db:
            statement = (
                select(AttendanceAuditLog)
                .where(AttendanceAuditLog.attendance_log_id == attendance_log_id)
                .order_by(AttendanceAuditLog.created_at.desc())
            )
            return list(db.scalars(statement))
