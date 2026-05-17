import json
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.core.timezone import VIETNAM_TZ, as_utc, as_vietnam_time, to_vietnam_iso, vietnam_today
from app.models.entities import AttendanceAuditLog, AttendanceLog, utc_now
from app.repositories.audit_repository import AttendanceAuditRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.system_config_repository import SystemConfigRepository
from app.services.anomaly_service import AnomalyService
from app.services.recognition_service import RecognitionService
from app.services.storage_service import ImageStorageService


class AttendanceService:
    def __init__(self) -> None:
        self.attendance_repository = AttendanceRepository()
        self.employee_repository = EmployeeRepository()
        self.config_repository = SystemConfigRepository()
        self.recognition_service = RecognitionService()
        self.storage_service = ImageStorageService()
        self.anomaly_service = AnomalyService()
        self.audit_repository = AttendanceAuditRepository()

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

        liveness = self.recognition_service.detect_liveness(cropped_image_base64)
        if self.recognition_service.is_spoof(liveness):
            return {
                **recognized,
                "is_live": False,
                "action_suggested": "ignored",
                "attendance_status": "rejected",
                "message": "Phat hien khuon mat gia (anh in / man hinh)",
                "liveness_score": round(liveness.get("score", 0.0), 4),
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

        liveness = self.recognition_service.detect_liveness(cropped_image_base64)
        is_live_final = liveness["is_real"] if liveness.get("assessed") else is_live

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

        if self.recognition_service.is_spoof(liveness):
            return {
                "match_found": True,
                "employee_id": employee_id,
                "employee_name": employee.full_name,
                "score": score,
                "threshold": threshold,
                "is_live": False,
                "action_suggested": "ignored",
                "attendance_status": "rejected",
                "message": "Phat hien khuon mat gia (anh in / man hinh) - khong ghi cong",
                "snapshot_url": snapshot_url,
                "liveness_score": round(liveness.get("score", 0.0), 4),
            }

        log = AttendanceLog(
            employee_id=employee_id,
            device_id=device_id,
            action_type=action,
            event_time=now,
            score=score,
            threshold=threshold,
            is_live=is_live_final,
            snapshot_url=snapshot_url,
            status="recorded",
            reason=None,
            created_at=now,
        )
        created_log = self.attendance_repository.create(log)
        flags = self.anomaly_service.evaluate_attendance_log(created_log)
        final_status = "suspicious" if flags else created_log.status

        if flags:
            message = "Attendance recorded but marked suspicious"
        else:
            message = "Check-in thanh cong" if action == "check_in" else "Check-out thanh cong"
        return {
            "match_found": True,
            "employee_id": employee_id,
            "employee_name": employee.full_name,
            "score": score,
            "threshold": threshold,
            "is_live": is_live_final,
            "action_suggested": action,
            "attendance_status": final_status,
            "message": message,
            "snapshot_url": snapshot_url,
            "liveness_score": round(liveness.get("score", 0.0), 4),
            "anomaly_flags": [flag.rule_key for flag in flags],
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

    def update_log(self, log_id: int, payload: dict, actor_user: dict) -> dict:
        log = self.attendance_repository.get(log_id)
        if log is None:
            return {
                "updated": False,
                "message": "Attendance log not found",
            }

        allowed_fields = {"action_type", "status", "reason"}
        changed_payload = {
            key: value
            for key, value in payload.items()
            if key in allowed_fields and value is not None and getattr(log, key) != value
        }
        if not changed_payload:
            employee = self.employee_repository.get(log.employee_id)
            return {
                "updated": False,
                "message": "No changes to update",
                "log": self._to_log_item(log, employee),
            }

        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reason is required when editing attendance logs",
            )

        before_value = {
            key: getattr(log, key)
            for key in changed_payload
        }
        for key, value in payload.items():
            if key in allowed_fields and value is not None:
                setattr(log, key, value)

        updated_log = self.attendance_repository.update(log)
        after_value = {
            key: getattr(updated_log, key)
            for key in changed_payload
        }
        self.audit_repository.create(
            AttendanceAuditLog(
                attendance_log_id=updated_log.id,
                actor_user_id=actor_user.get("id"),
                actor_username=actor_user.get("username", "unknown"),
                action="update_attendance_log",
                before_value=json.dumps(before_value),
                after_value=json.dumps(after_value),
                reason=reason,
                created_at=utc_now(),
            )
        )
        employee = self.employee_repository.get(updated_log.employee_id)
        return {
            "updated": True,
            "message": "Attendance log updated",
            "log": self._to_log_item(updated_log, employee),
        }

    def list_audit_logs(self, log_id: int) -> list[dict]:
        items = self.audit_repository.list_by_log(log_id)
        return [
            {
                "id": item.id,
                "attendance_log_id": item.attendance_log_id,
                "actor_user_id": item.actor_user_id,
                "actor_username": item.actor_username,
                "action": item.action,
                "before_value": json.loads(item.before_value),
                "after_value": json.loads(item.after_value),
                "reason": item.reason,
                "created_at": to_vietnam_iso(item.created_at),
            }
            for item in items
        ]

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
