import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings
from app.core.timezone import to_vietnam_iso
from app.models.entities import AnomalyFlag, AttendanceLog, Employee

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def send_anomaly_alerts(
        self,
        flags: list[AnomalyFlag],
        attendance_log: AttendanceLog,
        employee: Employee | None,
    ) -> None:
        if not flags or not self._anomaly_email_enabled():
            return

        message = EmailMessage()
        message["Subject"] = f"[Face Attendance] {len(flags)} anomaly alert(s)"
        message["From"] = self._from_address()
        message["To"] = ", ".join(self.settings.alert_email_recipients)
        message.set_content(self._build_body(flags, attendance_log, employee))

        try:
            self._send_message(message)
        except Exception as exc:
            logger.warning("Could not send anomaly email alert: %s", exc)

    def send_attendance_receipt(
        self,
        attendance_log: AttendanceLog,
        employee: Employee,
    ) -> tuple[bool, str | None]:
        if not self._smtp_enabled():
            return False, "SMTP is not configured"
        if not employee.email:
            return False, "Employee email is empty"

        message = EmailMessage()
        action_text = "check-in" if attendance_log.action_type == "check_in" else "check-out"
        message["Subject"] = f"[Face Attendance] {action_text.title()} recorded"
        message["From"] = self._from_address()
        message["To"] = employee.email
        message.set_content(
            "\n".join(
                [
                    f"Hello {employee.full_name},",
                    "",
                    f"Your {action_text} was recorded.",
                    "",
                    f"Time: {to_vietnam_iso(attendance_log.event_time)}",
                    f"Device: {attendance_log.device_id}",
                    f"Status: {attendance_log.status}",
                    f"AI score: {attendance_log.score}",
                    "",
                    "If this record is incorrect, please contact your manager.",
                ]
            )
        )

        try:
            self._send_message(message)
        except Exception as exc:
            logger.warning("Could not send attendance receipt email: %s", exc)
            return False, str(exc)
        return True, None

    def send_daily_attendance_summary(
        self,
        employee: Employee,
        work_date: str,
        summary: dict,
    ) -> tuple[bool, str | None]:
        if not self._smtp_enabled():
            return False, "SMTP is not configured"
        if not employee.email:
            return False, "Employee email is empty"

        message = EmailMessage()
        message["Subject"] = f"[Face Attendance] Daily attendance summary {work_date}"
        message["From"] = self._from_address()
        message["To"] = employee.email
        message.set_content(self._build_daily_summary_body(employee, work_date, summary))

        try:
            self._send_message(message)
        except Exception as exc:
            logger.warning("Could not send daily attendance summary: %s", exc)
            return False, str(exc)
        return True, None

    def _anomaly_email_enabled(self) -> bool:
        return bool(
            self.settings.alert_email_enabled
            and self._smtp_enabled()
            and self.settings.alert_email_recipients
        )

    def _smtp_enabled(self) -> bool:
        return bool(self.settings.alert_smtp_host)

    def _from_address(self) -> str:
        return self.settings.alert_smtp_from or self.settings.alert_smtp_username or "alerts@example.local"

    def _send_message(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.settings.alert_smtp_host, self.settings.alert_smtp_port, timeout=15) as smtp:
            if self.settings.alert_smtp_use_tls:
                smtp.starttls()
            if self.settings.alert_smtp_username and self.settings.alert_smtp_password:
                smtp.login(self.settings.alert_smtp_username, self.settings.alert_smtp_password)
            smtp.send_message(message)

    def _build_body(
        self,
        flags: list[AnomalyFlag],
        attendance_log: AttendanceLog,
        employee: Employee | None,
    ) -> str:
        employee_name = employee.full_name if employee else f"Employee #{attendance_log.employee_id}"
        lines = [
            "Attendance anomaly detected.",
            "",
            f"Employee: {employee_name}",
            f"Device: {attendance_log.device_id}",
            f"Action: {attendance_log.action_type}",
            f"Event time: {to_vietnam_iso(attendance_log.event_time)}",
            f"Score: {attendance_log.score}",
            f"Log ID: {attendance_log.id}",
            "",
            "Flags:",
        ]
        for flag in flags:
            lines.append(f"- [{flag.severity}] {flag.title}: {flag.description}")
        return "\n".join(lines)

    def _build_daily_summary_body(self, employee: Employee, work_date: str, summary: dict) -> str:
        lines = [
            f"Hello {employee.full_name},",
            "",
            f"Attendance summary for {work_date}:",
            "",
            f"Status: {summary['status_label']}",
        ]

        if summary.get("shift_name"):
            lines.append(f"Shift: {summary['shift_name']} ({summary['shift_start']} - {summary['shift_end']})")
        if summary.get("check_in_time"):
            lines.append(f"Check-in: {summary['check_in_time']}")
        if summary.get("check_out_time"):
            lines.append(f"Check-out: {summary['check_out_time']}")
        if summary.get("late_minutes") is not None:
            lines.append(f"Late: {summary['late_minutes']} minute(s)")
        if summary.get("early_leave_minutes") is not None:
            lines.append(f"Early leave: {summary['early_leave_minutes']} minute(s)")

        reason = summary.get("reason")
        if reason:
            lines.extend(["", f"Reason: {reason}"])

        lines.extend(
            [
                "",
                "If this summary is incorrect, please contact your manager.",
            ]
        )
        return "\n".join(lines)
