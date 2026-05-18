from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.timezone import VIETNAM_TZ, as_utc, to_vietnam_iso, vietnam_today
from app.models.entities import AnomalyFlag, AttendanceLog, utc_now
from app.repositories.anomaly_repository import AnomalyFlagRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.system_config_repository import SystemConfigRepository
from app.services.alert_service import AlertService


class AnomalyService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.anomaly_repository = AnomalyFlagRepository()
        self.attendance_repository = AttendanceRepository()
        self.employee_repository = EmployeeRepository()
        self.config_repository = SystemConfigRepository()
        self.alert_service = AlertService()

    def evaluate_attendance_log(self, log: AttendanceLog) -> list[AnomalyFlag]:
        flags = self._build_flags(log)
        created_flags = self.anomaly_repository.create_many(flags)

        if created_flags and log.status != "suspicious":
            log.status = "suspicious"
            self.attendance_repository.update(log)

        if created_flags:
            employee = self.employee_repository.get(log.employee_id)
            self.alert_service.send_anomaly_alerts(created_flags, log, employee)

        return created_flags

    def list_flags(
        self,
        status: str | None = "open",
        today_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        date_from = None
        date_to = None
        if today_only:
            date_from, date_to = self._today_bounds()

        flags = self.anomaly_repository.list(
            status=status,
            date_from=date_from,
            date_to=date_to,
            limit=max(1, min(limit, 200)),
        )
        log_ids = [flag.attendance_log_id for flag in flags]
        logs_by_id = {log.id: log for log in self._list_logs_by_ids(log_ids)}
        employee_ids = [flag.employee_id for flag in flags]
        employees_by_id = {
            employee.id: employee
            for employee in self.employee_repository.list_by_ids(employee_ids)
        }

        return [
            self._to_flag_item(
                flag,
                logs_by_id.get(flag.attendance_log_id),
                employees_by_id.get(flag.employee_id),
            )
            for flag in flags
        ]

    def mark_reviewed(self, flag_id: int, reviewer_user_id: int, note: str) -> dict:
        flag = self.anomaly_repository.mark_reviewed(flag_id, reviewer_user_id, note)
        if flag is None:
            return {"updated": False, "message": "Anomaly flag not found"}
        return {"updated": True, "message": "Anomaly flag reviewed", "flag_id": flag.id}

    def open_today_count(self) -> int:
        start, end = self._today_bounds()
        return len(self.anomaly_repository.list(status="open", date_from=start, date_to=end))

    def _build_flags(self, log: AttendanceLog) -> list[AnomalyFlag]:
        flags: list[AnomalyFlag] = []
        safe_score_threshold = self.config_repository.get_float(
            "anomaly_safe_score_threshold",
            self.settings.anomaly_safe_score_threshold,
        )
        short_session_minutes = self.config_repository.get_int(
            "anomaly_short_session_minutes",
            self.settings.anomaly_short_session_minutes,
        )
        near_event_minutes = self.config_repository.get_int(
            "anomaly_near_event_minutes",
            self.settings.anomaly_near_event_minutes,
        )

        if log.score < safe_score_threshold:
            flags.append(
                self._flag(
                    log,
                    rule_key="low_confidence",
                    severity="warning",
                    title="Low confidence attendance",
                    description=(
                        f"AI score {log.score:.2f} is below safe threshold "
                        f"{safe_score_threshold:.2f}."
                    ),
                )
            )

        window_start = log.event_time - timedelta(minutes=max(short_session_minutes, near_event_minutes))
        recent_logs = [
            item
            for item in self.attendance_repository.list(date_from=window_start, date_to=log.event_time)
            if item.id != log.id and item.status in {"recorded", "suspicious"}
        ]

        same_employee_recent = [
            item
            for item in recent_logs
            if item.employee_id == log.employee_id
        ]
        last_same_employee = same_employee_recent[0] if same_employee_recent else None
        if (
            last_same_employee
            and last_same_employee.action_type != log.action_type
            and self._minutes_between(last_same_employee.event_time, log.event_time) < short_session_minutes
        ):
            flags.append(
                self._flag(
                    log,
                    rule_key="short_checkin_checkout_gap",
                    severity="critical",
                    title="Check-in/out gap too short",
                    description=(
                        f"Previous {last_same_employee.action_type} at "
                        f"{to_vietnam_iso(last_same_employee.event_time)} is less than "
                        f"{short_session_minutes} minutes from this {log.action_type}."
                    ),
                )
            )

        different_device_logs = [
            item
            for item in same_employee_recent
            if item.device_id != log.device_id
            and self._minutes_between(item.event_time, log.event_time) < near_event_minutes
        ]
        if different_device_logs:
            other = different_device_logs[0]
            flags.append(
                self._flag(
                    log,
                    rule_key="same_employee_multiple_kiosks",
                    severity="critical",
                    title="Same employee at multiple kiosks",
                    description=(
                        f"Employee was recorded at {other.device_id} and {log.device_id} "
                        f"within {near_event_minutes} minutes."
                    ),
                )
            )

        nearby_different_employee = [
            item
            for item in recent_logs
            if item.employee_id != log.employee_id
            and item.device_id == log.device_id
            and item.action_type == log.action_type
            and self._minutes_between(item.event_time, log.event_time) < near_event_minutes
        ]
        if nearby_different_employee:
            flags.append(
                self._flag(
                    log,
                    rule_key="nearby_different_employee_same_kiosk",
                    severity="warning",
                    title="Multiple employees same action near same time",
                    description=(
                        f"Another employee had {log.action_type} on {log.device_id} "
                        f"within {near_event_minutes} minutes. Review if this was a queue or misrecognition."
                    ),
                )
            )

        return flags

    def _list_logs_by_ids(self, log_ids: list[int]) -> list[AttendanceLog]:
        if not log_ids:
            return []
        id_set = set(log_ids)
        return [log for log in self.attendance_repository.list(limit=500) if log.id in id_set]

    def _flag(
        self,
        log: AttendanceLog,
        rule_key: str,
        severity: str,
        title: str,
        description: str,
    ) -> AnomalyFlag:
        return AnomalyFlag(
            attendance_log_id=log.id,
            employee_id=log.employee_id,
            rule_key=rule_key,
            severity=severity,
            title=title,
            description=description,
            status="open",
            created_at=utc_now(),
        )

    def _to_flag_item(self, flag: AnomalyFlag, log: AttendanceLog | None, employee) -> dict:
        return {
            "id": flag.id,
            "attendance_log_id": flag.attendance_log_id,
            "employee_id": flag.employee_id,
            "employee_name": employee.full_name if employee else "Unknown",
            "rule_key": flag.rule_key,
            "severity": flag.severity,
            "title": flag.title,
            "description": flag.description,
            "status": flag.status,
            "created_at": to_vietnam_iso(flag.created_at),
            "reviewed_at": to_vietnam_iso(flag.reviewed_at) if flag.reviewed_at else None,
            "resolution_note": flag.resolution_note,
            "device_id": log.device_id if log else None,
            "action_type": log.action_type if log else None,
            "event_time": to_vietnam_iso(log.event_time) if log else None,
            "score": log.score if log else None,
        }

    def _today_bounds(self) -> tuple[datetime, datetime]:
        today = vietnam_today()
        return (
            as_utc(datetime.combine(today, datetime.min.time(), tzinfo=VIETNAM_TZ)),
            as_utc(datetime.combine(today, datetime.max.time(), tzinfo=VIETNAM_TZ)),
        )

    @staticmethod
    def _minutes_between(first: datetime, second: datetime) -> float:
        return abs((second - first).total_seconds()) / 60
