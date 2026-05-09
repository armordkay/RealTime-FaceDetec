from datetime import datetime

from sqlalchemy import select

from app.db.session import session_scope
from app.models.entities import AttendanceLog


class AttendanceRepository:
    def create(self, log: AttendanceLog) -> AttendanceLog:
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
    ) -> list[AttendanceLog]:
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
            return list(db.scalars(statement))

    def get_last_for_employee(self, employee_id: int) -> AttendanceLog | None:
        with session_scope() as db:
            statement = (
                select(AttendanceLog)
                .where(AttendanceLog.employee_id == employee_id)
                .order_by(AttendanceLog.event_time.desc())
                .limit(1)
            )
            return db.scalar(statement)

    def get(self, log_id: int) -> AttendanceLog | None:
        with session_scope() as db:
            return db.get(AttendanceLog, log_id)

    def update(self, log: AttendanceLog) -> AttendanceLog:
        with session_scope() as db:
            merged = db.merge(log)
            db.flush()
            db.refresh(merged)
            return merged
