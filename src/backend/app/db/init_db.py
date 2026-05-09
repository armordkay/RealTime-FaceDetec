from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.core.timezone import as_utc, vietnam_now
from app.db.base import Base
from app.db.session import engine, session_scope
from app.models.entities import AttendanceLog, Employee, Shift, SystemConfig, User, utc_now


DEFAULT_CONFIGS = {
    "recognition_threshold": ("0.65", "Minimum score required to accept a face match"),
    "attendance_cooldown_seconds": ("60", "Seconds to block duplicate check-in/out events"),
    "kiosk_allowed_devices": ("kiosk_front_gate_1,camera_front_door_1", "Comma-separated device ids allowed for kiosk use"),
}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    seed_db()


def seed_db() -> None:
    with session_scope() as db:
        _seed_system_configs(db)
        _seed_admin_user(db)

        has_employees = db.scalar(select(Employee.id).limit(1)) is not None
        has_shifts = db.scalar(select(Shift.id).limit(1)) is not None

        if has_employees or has_shifts:
            return

        now = utc_now()
        today_vn = vietnam_now()
        yesterday_vn = today_vn - timedelta(days=1)

        def local_log_time(base: datetime, hour: int, minute: int):
            return as_utc(base.replace(hour=hour, minute=minute, second=0, microsecond=0))

        day_shift = Shift(
            name="Day Shift",
            start_time="08:30",
            end_time="17:30",
            late_tolerance_minutes=10,
            early_leave_tolerance_minutes=10,
            checkin_open_minutes_before=30,
            checkout_open_minutes_before=30,
            is_overnight=False,
            created_at=now,
        )
        db.add(day_shift)
        db.flush()

        employees = [
            Employee(
                employee_code="EMP001",
                full_name="Nguyen Van A",
                email="a@example.com",
                phone="0901000001",
                department="IT",
                position="Backend Engineer",
                status="active",
                default_shift_id=day_shift.id,
                created_at=now,
                updated_at=now,
            ),
            Employee(
                employee_code="EMP002",
                full_name="Tran Van Manager",
                email="manager_staff@example.com",
                phone="0901000002",
                department="IT",
                position="Team Manager",
                status="active",
                default_shift_id=day_shift.id,
                created_at=now,
                updated_at=now,
            ),
            Employee(
                employee_code="EMP003",
                full_name="Le Thi Ke Toan",
                email="finance@example.com",
                phone="0901000003",
                department="Finance",
                position="Accountant",
                status="active",
                default_shift_id=day_shift.id,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(employees)
        db.flush()

        db.add(
            User(
                username="manager",
                email="manager@example.com",
                password_hash=hash_password("manager123"),
                role="manager",
                is_active=True,
                employee_id=employees[1].id,
                created_at=now,
                updated_at=now,
            )
        )

        db.add_all(
            [
                AttendanceLog(
                    employee_id=employees[0].id,
                    device_id="camera_front_door_1",
                    action_type="check_in",
                    event_time=local_log_time(yesterday_vn, 8, 35),
                    score=0.91,
                    threshold=0.65,
                    is_live=True,
                    snapshot_url="/media/snapshots/yesterday/emp_1_checkin.jpg",
                    status="recorded",
                    reason=None,
                    created_at=local_log_time(yesterday_vn, 8, 35),
                ),
                AttendanceLog(
                    employee_id=employees[0].id,
                    device_id="camera_front_door_1",
                    action_type="check_out",
                    event_time=local_log_time(yesterday_vn, 17, 40),
                    score=0.89,
                    threshold=0.65,
                    is_live=True,
                    snapshot_url="/media/snapshots/yesterday/emp_1_checkout.jpg",
                    status="recorded",
                    reason=None,
                    created_at=local_log_time(yesterday_vn, 17, 40),
                ),
                AttendanceLog(
                    employee_id=employees[1].id,
                    device_id="camera_front_door_1",
                    action_type="check_in",
                    event_time=local_log_time(today_vn, 8, 25),
                    score=0.93,
                    threshold=0.65,
                    is_live=True,
                    snapshot_url="/media/snapshots/today/emp_2_checkin.jpg",
                    status="recorded",
                    reason=None,
                    created_at=local_log_time(today_vn, 8, 25),
                ),
                AttendanceLog(
                    employee_id=employees[2].id,
                    device_id="camera_finance_gate_1",
                    action_type="check_in",
                    event_time=local_log_time(today_vn, 8, 45),
                    score=0.90,
                    threshold=0.65,
                    is_live=True,
                    snapshot_url="/media/snapshots/today/emp_3_checkin.jpg",
                    status="recorded",
                    reason=None,
                    created_at=local_log_time(today_vn, 8, 45),
                ),
            ]
        )


def _seed_system_configs(db) -> None:
    for key, (value, description) in DEFAULT_CONFIGS.items():
        if db.get(SystemConfig, key) is None:
            db.add(
                SystemConfig(
                    key=key,
                    value=value,
                    description=description,
                    updated_at=utc_now(),
                )
            )


def _seed_admin_user(db) -> None:
    existing_admin = db.scalar(select(User).where(User.username == "admin"))
    if existing_admin is not None:
        return

    db.add(
        User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="admin",
            is_active=True,
            employee_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )
