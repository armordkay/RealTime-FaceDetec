from datetime import datetime, timedelta

from app.core.timezone import VIETNAM_TZ, as_utc, as_vietnam_time, to_vietnam_iso, vietnam_today
from app.models.entities import AttendanceLog, utc_now
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.system_config_repository import SystemConfigRepository
from app.services.recognition_service import RecognitionService
from app.services.storage_service import ImageStorageService


class AttendanceService:
    def __init__(self) -> None:
        self.attendance_repository = AttendanceRepository()
        self.employee_repository = EmployeeRepository()
        self.config_repository = SystemConfigRepository()
        self.recognition_service = RecognitionService()
        self.storage_service = ImageStorageService()

    def recognize_and_attend(self, device_id: str, cropped_image_base64: str) -> dict:
        preview = self.recognize_for_attendance(device_id, cropped_image_base64)
        if preview.get("attendance_status") != "pending_confirmation":
            return preview

        return self.confirm_attendance(
            employee_id=preview["employee_id"],
            device_id=device_id,
            cropped_image_base64=cropped_image_base64,
            score=preview["score"],
            threshold=preview["threshold"],
            is_live=preview["is_live"],
        )

    def recognize_for_attendance(self, device_id: str, cropped_image_base64: str) -> dict:
        if not self._is_device_allowed(device_id):
            return {
                "match_found": False,
                "employee_id": None,
                "employee_name": None,
                "score": 0.0,
                "threshold": self.recognition_service.get_threshold(),
                "is_live": True,
                "action_suggested": "ignored",
                "attendance_status": "rejected",
                "message": "Device is not allowed",
                "snapshot_url": None,
            }

        recognized = self.recognition_service.recognize(cropped_image_base64=cropped_image_base64)
        if not recognized["match_found"]:
            return {
                **recognized,
                "action_suggested": "ignored",
                "attendance_status": "rejected",
                "snapshot_url": None,
            }

        employee_id = recognized["employee_id"]
        employee = self.employee_repository.get(employee_id)
        if employee is None:
            return {
                **recognized,
                "action_suggested": "ignored",
                "attendance_status": "rejected",
                "message": "Employee not found",
                "snapshot_url": None,
            }

        action = self._suggest_action(employee_id)
        return {
            **recognized,
            "action_suggested": action,
            "attendance_status": "pending_confirmation",
            "message": "Ready to record",
            "snapshot_url": None,
        }

    def confirm_attendance(
        self,
        employee_id: int,
        device_id: str,
        cropped_image_base64: str,
        score: float,
        threshold: float,
        is_live: bool,
    ) -> dict:
        if not self._is_device_allowed(device_id):
            return {
                "match_found": False,
                "employee_id": employee_id,
                "employee_name": None,
                "score": score,
                "threshold": threshold,
                "is_live": is_live,
                "action_suggested": "ignored",
                "attendance_status": "rejected",
                "message": "Device is not allowed",
                "snapshot_url": None,
            }

        employee = self.employee_repository.get(employee_id)
        if employee is None:
            return {
                "match_found": False,
                "employee_id": employee_id,
                "employee_name": None,
                "score": score,
                "threshold": threshold,
                "is_live": is_live,
                "action_suggested": "ignored",
                "attendance_status": "rejected",
                "message": "Employee not found",
                "snapshot_url": None,
            }

        now = utc_now()
        action = self._suggest_action(employee_id)
        try:
            snapshot_url = self.storage_service.save_base64_image(
                cropped_image_base64,
                folder=f"snapshots/{as_vietnam_time(now).date().isoformat()}",
                prefix=f"emp_{employee_id}_{action}",
            )
        except ValueError:
            return {
                "match_found": True,
                "employee_id": employee_id,
                "employee_name": employee.full_name,
                "score": score,
                "threshold": threshold,
                "is_live": is_live,
                "action_suggested": "ignored",
                "attendance_status": "rejected",
                "message": "Invalid image payload",
                "snapshot_url": None,
            }

        log = AttendanceLog(
            employee_id=employee_id,
            device_id=device_id,
            action_type=action,
            event_time=now,
            score=score,
            threshold=threshold,
            is_live=is_live,
            snapshot_url=snapshot_url,
            status="recorded",
            reason=None,
            created_at=now,
        )
        self.attendance_repository.create(log)

        message = "Check-in thanh cong" if action == "check_in" else "Check-out thanh cong"
        return {
            "match_found": True,
            "employee_id": employee_id,
            "employee_name": employee.full_name,
            "score": score,
            "threshold": threshold,
            "is_live": is_live,
            "action_suggested": action,
            "attendance_status": "recorded",
            "message": message,
            "snapshot_url": snapshot_url,
        }

    def list_logs(
        self,
        employee_id: int | None,
        date_from: str | None,
        date_to: str | None,
        status: str | None,
        action_type: str | None,
        device_id: str | None,
        limit: int | None = None,
    ) -> list[dict]:
        from_dt = self._parse_date(date_from, start=True)
        to_dt = self._parse_date(date_to, start=False)
        logs = self.attendance_repository.list(
            employee_id=employee_id,
            status=status,
            action_type=action_type,
            date_from=from_dt,
            date_to=to_dt,
            device_id=device_id,
            limit=limit,
        )

        employees_by_id = {
            employee.id: employee
            for employee in self.employee_repository.list_by_ids([log.employee_id for log in logs])
        }
        return [self._to_log_item(log, employees_by_id.get(log.employee_id)) for log in logs]

    def my_logs(self, employee_id: int) -> list[dict]:
        return self.list_logs(
            employee_id=employee_id,
            date_from=None,
            date_to=None,
            status=None,
            action_type=None,
            device_id=None,
        )

    def my_status(self, employee_id: int) -> dict:
        today = vietnam_today()
        start_of_day, end_of_day = self._today_bounds()
        today_logs = self.attendance_repository.list(
            employee_id=employee_id,
            status="recorded",
            date_from=start_of_day,
            date_to=end_of_day,
        )
        check_in_count = len([item for item in today_logs if item.action_type == "check_in"])
        check_out_count = len([item for item in today_logs if item.action_type == "check_out"])
        last_log = today_logs[0] if today_logs else None
        employee = self.employee_repository.get(employee_id)

        return {
            "employee_id": employee_id,
            "employee_name": employee.full_name if employee else "Unknown",
            "date": today.isoformat(),
            "check_in_count": check_in_count,
            "check_out_count": check_out_count,
            "last_action": last_log.action_type if last_log else None,
            "last_status": last_log.status if last_log else None,
            "last_event_time": to_vietnam_iso(last_log.event_time) if last_log else None,
            "next_expected_action": self._suggest_action(employee_id),
        }

    def update_log(self, log_id: int, payload: dict) -> dict:
        log = self.attendance_repository.get(log_id)
        if log is None:
            return {
                "updated": False,
                "message": "Attendance log not found",
            }

        allowed_fields = {"action_type", "status", "reason"}
        for key, value in payload.items():
            if key in allowed_fields and value is not None:
                setattr(log, key, value)

        self.attendance_repository.update(log)
        employee = self.employee_repository.get(log.employee_id)
        return {
            "updated": True,
            "message": "Attendance log updated",
            "log": self._to_log_item(log, employee),
        }

    def _suggest_action(self, employee_id: int) -> str:
        start_of_day, end_of_day = self._today_bounds()
        logs = self.attendance_repository.list(
            employee_id=employee_id,
            status="recorded",
            date_from=start_of_day,
            date_to=end_of_day,
            limit=1,
        )
        if not logs:
            return "check_in"

        last = logs[0]
        return "check_out" if last.action_type == "check_in" else "check_in"

    def _today_bounds(self) -> tuple[datetime, datetime]:
        today = vietnam_today()
        return (
            as_utc(datetime.combine(today, datetime.min.time(), tzinfo=VIETNAM_TZ)),
            as_utc(datetime.combine(today, datetime.max.time(), tzinfo=VIETNAM_TZ)),
        )

    def _to_log_item(self, log: AttendanceLog, employee) -> dict:
        return {
            "id": log.id,
            "employee_id": log.employee_id,
            "employee_name": employee.full_name if employee else "Unknown",
            "device_id": log.device_id,
            "action_type": log.action_type,
            "event_time": to_vietnam_iso(log.event_time),
            "event_time_vn": to_vietnam_iso(log.event_time),
            "score": log.score,
            "threshold": log.threshold,
            "is_live": log.is_live,
            "snapshot_url": log.snapshot_url,
            "status": log.status,
            "reason": log.reason,
            "created_at": to_vietnam_iso(log.created_at),
        }

    def _parse_date(self, value: str | None, start: bool) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=VIETNAM_TZ)
        parsed = as_utc(parsed)

        if start:
            return parsed
        return parsed + timedelta(hours=23, minutes=59, seconds=59)

    def _is_device_allowed(self, device_id: str) -> bool:
        raw = self.config_repository.get_value("kiosk_allowed_devices", "")
        allowed = {item.strip() for item in raw.split(",") if item.strip()}
        return not allowed or device_id in allowed
