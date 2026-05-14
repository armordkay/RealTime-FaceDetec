from collections import defaultdict
from datetime import datetime

from app.core.timezone import as_vietnam_time, to_vietnam_iso, vietnam_now
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.employee_repository import EmployeeRepository


class ReportService:
    def __init__(self) -> None:
        self.attendance_repository = AttendanceRepository()
        self.employee_repository = EmployeeRepository()

    def attendance_daily(self, date_value: str | None = None) -> list[dict]:
        if date_value:
            try:
                target_date = datetime.fromisoformat(date_value).date()
            except ValueError:
                target_date = vietnam_now().date()
        else:
            target_date = vietnam_now().date()

        logs = self.attendance_repository.list()
        grouped: dict[int, list] = defaultdict(list)
        for item in logs:
            if as_vietnam_time(item.event_time).date() == target_date:
                grouped[item.employee_id].append(item)

        items = []
        employees_by_id = {
            employee.id: employee
            for employee in self.employee_repository.list_by_ids(list(grouped.keys()))
        }
        for employee_id, values in grouped.items():
            employee = employees_by_id.get(employee_id)
            check_in_count = len([v for v in values if v.action_type == "check_in" and v.status == "recorded"])
            check_out_count = len([v for v in values if v.action_type == "check_out" and v.status == "recorded"])
            last_status = values[-1].status if values else "unknown"
            items.append(
                {
                    "employee_id": employee_id,
                    "employee_name": employee.full_name if employee else "Unknown",
                    "check_in_count": check_in_count,
                    "check_out_count": check_out_count,
                    "last_status": last_status,
                }
            )
        return items

    def attendance_monthly(self, month: str | None = None) -> dict:
        if month:
            try:
                year, month_num = [int(part) for part in month.split("-")]
            except Exception:
                now = vietnam_now()
                year, month_num = now.year, now.month
        else:
            now = vietnam_now()
            year, month_num = now.year, now.month

        logs = self.attendance_repository.list()
        recorded = [
            log
            for log in logs
            if as_vietnam_time(log.event_time).year == year
            and as_vietnam_time(log.event_time).month == month_num
            and log.status == "recorded"
        ]
        return {
            "month": f"{year:04d}-{month_num:02d}",
            "recorded_events": len(recorded),
            "employee_active": len({item.employee_id for item in recorded}),
        }

    def late_employees(self) -> list[dict]:
        # Mock metric: employees with odd id are marked late in MVP mock mode.
        employees = self.employee_repository.list(status="active")
        return [
            {
                "employee_id": item.id,
                "employee_name": item.full_name,
                "late_count": 1,
            }
            for item in employees
            if item.id % 2 == 1
        ]

    def export_csv(self) -> str:
        rows = ["employee_id,employee_name,action_type,event_time,status"]
        logs = self.attendance_repository.list()
        employees_by_id = {
            employee.id: employee
            for employee in self.employee_repository.list_by_ids([log.employee_id for log in logs])
        }
        for log in logs:
            employee = employees_by_id.get(log.employee_id)
            rows.append(
                f"{log.employee_id},{employee.full_name if employee else 'Unknown'},{log.action_type},{to_vietnam_iso(log.event_time)},{log.status}"
            )
        return "\n".join(rows)
