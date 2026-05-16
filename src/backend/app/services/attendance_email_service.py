import logging
from datetime import date, datetime, time, timedelta

from app.core.config import get_settings
from app.core.timezone import VIETNAM_TZ, as_utc, as_vietnam_time, to_vietnam_iso, vietnam_now
from app.models.entities import DailyAttendanceEmailNotification, Employee, utc_now
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.daily_attendance_email_repository import DailyAttendanceEmailNotificationRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.leave_calendar_repository import LeaveCalendarRepository
from app.repositories.shift_repository import ShiftRepository
from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)


class AttendanceEmailService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.attendance_repository = AttendanceRepository()
        self.employee_repository = EmployeeRepository()
        self.shift_repository = ShiftRepository()
        self.leave_repository = LeaveCalendarRepository()
        self.notification_repository = DailyAttendanceEmailNotificationRepository()
        self.alert_service = AlertService()

    def process_due_notifications(self, limit: int = 200) -> dict:
        if not self.settings.attendance_email_enabled:
            return {"processed": 0, "sent": 0, "failed": 0, "message": "Attendance email disabled"}

        processed = 0
        sent = 0
        failed = 0
        for target_date in self._candidate_dates():
            if processed >= limit:
                break
            result = self._process_date(target_date, limit - processed)
            processed += result["processed"]
            sent += result["sent"]
            failed += result["failed"]

        if processed:
            logger.info("Daily attendance email worker processed=%d sent=%d failed=%d", processed, sent, failed)

        return {"processed": processed, "sent": sent, "failed": failed}

    def _process_date(self, target_date: date, limit: int) -> dict:
        employees = self.employee_repository.list(status="active")
        processed = 0
        sent = 0
        failed = 0

        for employee in employees:
            if processed >= limit:
                break

            work_date = target_date.isoformat()
            if self.notification_repository.get_by_employee_date(employee.id, work_date) is not None:
                continue

            shift = self._get_shift(employee)
            if shift is None or not self._is_shift_email_due(target_date, shift):
                continue

            summary = self._build_summary(employee, target_date, shift)
            processed += 1
            ok, error = self.alert_service.send_daily_attendance_summary(employee, work_date, summary)
            if ok:
                self._record(employee, work_date, "sent", summary["status"], None)
                sent += 1
            else:
                self._record(employee, work_date, "failed", summary["status"], error or "Email send failed")
                failed += 1

        return {"processed": processed, "sent": sent, "failed": failed}

    def _build_summary(self, employee: Employee, target_date: date, shift) -> dict:
        work_date = target_date.isoformat()
        shift_start = self._combine_local(target_date, shift.start_time)
        shift_end = self._combine_local(target_date, shift.end_time)
        if shift.is_overnight or shift_end <= shift_start:
            shift_end += timedelta(days=1)

        logs = self.attendance_repository.list(
            employee_id=employee.id,
            date_from=as_utc(datetime.combine(target_date, time.min, tzinfo=VIETNAM_TZ)),
            date_to=as_utc(datetime.combine(target_date, time.max, tzinfo=VIETNAM_TZ)),
        )
        recorded_logs = [log for log in logs if log.status in {"recorded", "suspicious"}]
        check_ins = sorted(
            [log for log in recorded_logs if log.action_type == "check_in"],
            key=lambda item: item.event_time,
        )
        check_outs = sorted(
            [log for log in recorded_logs if log.action_type == "check_out"],
            key=lambda item: item.event_time,
        )

        leave = self.leave_repository.find_for_employee_date(employee.id, work_date)
        first_check_in = check_ins[0] if check_ins else None
        last_check_out = check_outs[-1] if check_outs else None

        late_minutes = None
        early_leave_minutes = None
        status = "normal"
        status_label = "On time"
        reason_parts: list[str] = []

        if leave is not None:
            status = "leave"
            status_label = f"Approved {leave.leave_type}"
            if leave.reason:
                reason_parts.append(leave.reason)
        elif first_check_in is None and last_check_out is None:
            status = "absent"
            status_label = "Absent / no attendance record"

        if first_check_in is not None:
            late_minutes = max(0, int((as_vietnam_time(first_check_in.event_time) - shift_start).total_seconds() // 60))
            if late_minutes > shift.late_tolerance_minutes and status != "leave":
                status = "late"
                status_label = f"Late {late_minutes} minute(s)"
            if first_check_in.reason:
                reason_parts.append(first_check_in.reason)

        if last_check_out is not None:
            early_leave_minutes = max(0, int((shift_end - as_vietnam_time(last_check_out.event_time)).total_seconds() // 60))
            if early_leave_minutes > shift.early_leave_tolerance_minutes and status != "leave":
                status = "early_leave" if status == "normal" else f"{status}_early_leave"
                status_label = f"{status_label}; early leave {early_leave_minutes} minute(s)"
            if last_check_out.reason:
                reason_parts.append(last_check_out.reason)

        return {
            "status": status,
            "status_label": status_label,
            "shift_name": shift.name,
            "shift_start": shift.start_time,
            "shift_end": shift.end_time,
            "check_in_time": to_vietnam_iso(first_check_in.event_time) if first_check_in else None,
            "check_out_time": to_vietnam_iso(last_check_out.event_time) if last_check_out else None,
            "late_minutes": late_minutes,
            "early_leave_minutes": early_leave_minutes,
            "reason": "; ".join(dict.fromkeys(reason_parts)),
        }

    def _record(
        self,
        employee: Employee,
        work_date: str,
        status: str,
        summary_status: str,
        error_message: str | None,
    ) -> None:
        self.notification_repository.create(
            DailyAttendanceEmailNotification(
                employee_id=employee.id,
                work_date=work_date,
                recipient_email=employee.email,
                status=status,
                summary_status=summary_status,
                error_message=error_message,
                sent_at=utc_now() if status == "sent" else None,
                created_at=utc_now(),
            )
        )

    def _get_shift(self, employee: Employee):
        if employee.default_shift_id is not None:
            shift = self.shift_repository.get(employee.default_shift_id)
            if shift is not None:
                return shift
        shifts = self.shift_repository.list()
        return shifts[0] if shifts else None

    def _is_shift_email_due(self, target_date: date, shift) -> bool:
        shift_end = self._combine_local(target_date, shift.end_time)
        shift_start = self._combine_local(target_date, shift.start_time)
        if shift.is_overnight or shift_end <= shift_start:
            shift_end += timedelta(days=1)
        due_at = shift_end + timedelta(minutes=self.settings.attendance_email_after_shift_minutes)
        return vietnam_now() >= due_at

    def _candidate_dates(self) -> list[date]:
        today = vietnam_now().date()
        return [today, today - timedelta(days=1)]

    @staticmethod
    def _combine_local(target_date: date, hhmm: str) -> datetime:
        hour, minute = [int(part) for part in hhmm.split(":")]
        return datetime.combine(target_date, time(hour=hour, minute=minute), tzinfo=VIETNAM_TZ)
