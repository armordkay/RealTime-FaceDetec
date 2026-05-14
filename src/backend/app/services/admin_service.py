from collections import Counter

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.permissions import ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER
from app.core.security import hash_password
from app.core.timezone import to_vietnam_iso
from app.models.entities import User, utc_now
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.system_config_repository import SystemConfigRepository
from app.repositories.user_repository import UserRepository


ALLOWED_ROLES = {ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER}


class AdminService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.user_repository = UserRepository()
        self.employee_repository = EmployeeRepository()
        self.attendance_repository = AttendanceRepository()
        self.config_repository = SystemConfigRepository()

    def overview(self) -> dict:
        employees = self.employee_repository.list()
        users = self.user_repository.list()
        logs = self.attendance_repository.list()
        recorded_logs = [item for item in logs if item.status == "recorded"]
        action_counts = Counter(item.action_type for item in recorded_logs)

        return {
            "employees_total": len(employees),
            "employees_active": len([item for item in employees if item.status == "active"]),
            "users_total": len(users),
            "users_active": len([item for item in users if item.is_active]),
            "attendance_events": len(recorded_logs),
            "check_in_events": action_counts.get("check_in", 0),
            "check_out_events": action_counts.get("check_out", 0),
            "devices_seen": len({item.device_id for item in logs}),
        }

    def recent_access_logs(self, limit: int = 50) -> list[dict]:
        limit = max(1, min(limit, 200))
        logs = self.attendance_repository.list(action_type=None)
        access_logs = [item for item in logs if item.action_type in {"check_in", "check_out"}]
        employee_ids = [log.employee_id for log in access_logs[:limit]]
        employees_by_id = {
            employee.id: employee
            for employee in self.employee_repository.list_by_ids(employee_ids)
        }

        items = []
        for log in access_logs[:limit]:
            employee = employees_by_id.get(log.employee_id)
            items.append(
                {
                    "id": log.id,
                    "employee_id": log.employee_id,
                    "employee_name": employee.full_name if employee else "Unknown",
                    "employee_code": employee.employee_code if employee else "-",
                    "device_id": log.device_id,
                    "action_type": log.action_type,
                    "event_time": to_vietnam_iso(log.event_time),
                    "event_time_vn": to_vietnam_iso(log.event_time),
                    "score": log.score,
                    "status": log.status,
                    "reason": log.reason,
                }
            )
        return items

    def list_users(self) -> list[dict]:
        return [self._to_user_item(user) for user in self.user_repository.list()]

    def create_user(self, payload: dict) -> dict:
        role = payload.get("role", ROLE_VIEWER)
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

        username = payload["username"].strip().lower()
        email = payload["email"].strip().lower()
        if self.user_repository.exists_by_username_or_email(username, email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

        employee_id = payload.get("employee_id")
        if employee_id is not None and self.employee_repository.get(employee_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee not found")

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(payload["password"]),
            role=role,
            is_active=True,
            employee_id=employee_id,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return self._to_user_item(self.user_repository.create(user))

    def update_user(self, user_id: int, payload: dict) -> dict:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        role = payload.get("role")
        if role is not None:
            if role not in ALLOWED_ROLES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
            user.role = role

        if "is_active" in payload and payload["is_active"] is not None:
            user.is_active = payload["is_active"]

        if "employee_id" in payload:
            employee_id = payload["employee_id"]
            if employee_id is not None and self.employee_repository.get(employee_id) is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee not found")
            user.employee_id = employee_id

        return self._to_user_item(self.user_repository.update(user))

    def get_config(self) -> dict:
        return {
            "recognition_threshold": self.config_repository.get_float(
                "recognition_threshold",
                self.settings.recognition_threshold,
            ),
            "kiosk_allowed_devices": self.config_repository.get_value(
                "kiosk_allowed_devices",
                "kiosk_front_gate_1",
            ),
        }

    def update_config(self, payload: dict) -> dict:
        self.config_repository.upsert(
            "recognition_threshold",
            str(payload["recognition_threshold"]),
            "Minimum score required to accept a face match",
        )
        self.config_repository.upsert(
            "kiosk_allowed_devices",
            payload.get("kiosk_allowed_devices", ""),
            "Comma-separated device ids allowed for kiosk use",
        )
        return self.get_config()

    def _to_user_item(self, user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "employee_id": user.employee_id,
            "created_at": to_vietnam_iso(user.created_at),
            "updated_at": to_vietnam_iso(user.updated_at),
        }
