from datetime import datetime

from sqlalchemy import select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import AttendanceLog


class AttendanceRepository:
    def create(self, log: AttendanceLog) -> AttendanceLog:
        if supabase_enabled():
            rows = get_supabase_client().insert("attendance_logs", model_to_payload(log, "attendance_logs"))
            return row_to_model(AttendanceLog, rows[0], "attendance_logs")

        with session_scope() as db:
            db.add(log)
            db.flush()
            db.refresh(log)
            return log

    def list(
        self,
        employee_id: int | None = None,
        status: str | None = None,
        action_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        device_id: str | None = None,
        limit: int | None = None,
    ) -> list[AttendanceLog]:
        if supabase_enabled():
            params: dict[str, str] = {"order": "event_time.desc"}
            if limit is not None:
                params["limit"] = str(limit)
            if employee_id is not None:
                params["employee_id"] = f"eq.{employee_id}"
            if status:
                params["status"] = f"eq.{status}"
            if action_type:
                params["action_type"] = f"eq.{action_type}"
            if date_from:
                params["event_time"] = f"gte.{date_from.isoformat()}"
            if date_to:
                params["event_time"] = f"lte.{date_to.isoformat()}"
            if date_from and date_to:
                params["and"] = f"(event_time.gte.{date_from.isoformat()},event_time.lte.{date_to.isoformat()})"
                params.pop("event_time", None)
            if device_id:
                params["device_id"] = f"eq.{device_id}"
            return [
                row_to_model(AttendanceLog, row, "attendance_logs")
                for row in get_supabase_client().select("attendance_logs", params)
            ]

        with session_scope() as db:
            statement = select(AttendanceLog)
            if employee_id is not None:
                statement = statement.where(AttendanceLog.employee_id == employee_id)
            if status:
                statement = statement.where(AttendanceLog.status == status)
            if action_type:
                statement = statement.where(AttendanceLog.action_type == action_type)
            if date_from:
                statement = statement.where(AttendanceLog.event_time >= date_from)
            if date_to:
                statement = statement.where(AttendanceLog.event_time <= date_to)
            if device_id:
                statement = statement.where(AttendanceLog.device_id == device_id)

            statement = statement.order_by(AttendanceLog.event_time.desc())
            if limit is not None:
                statement = statement.limit(limit)
            return list(db.scalars(statement))

    def get(self, log_id: int) -> AttendanceLog | None:
        if supabase_enabled():
            rows = get_supabase_client().select("attendance_logs", {"id": f"eq.{log_id}", "limit": "1"})
            return row_to_model(AttendanceLog, rows[0], "attendance_logs") if rows else None

        with session_scope() as db:
            return db.get(AttendanceLog, log_id)

    def update(self, log: AttendanceLog) -> AttendanceLog:
        if supabase_enabled():
            rows = get_supabase_client().update(
                "attendance_logs",
                {"id": f"eq.{log.id}"},
                model_to_payload(log, "attendance_logs"),
            )
            return row_to_model(AttendanceLog, rows[0], "attendance_logs")

        with session_scope() as db:
            merged = db.merge(log)
            db.flush()
            db.refresh(merged)
            return merged
