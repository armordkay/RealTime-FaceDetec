import asyncio
import logging

from app.core.config import get_settings
from app.services.attendance_email_service import AttendanceEmailService

logger = logging.getLogger(__name__)


class AttendanceEmailWorker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.task: asyncio.Task | None = None

    def start(self) -> None:
        if not self.settings.attendance_email_enabled:
            logger.info("Attendance email worker disabled")
            return
        if self.task is not None and not self.task.done():
            return
        self.task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self.task is None or self.task.done():
            return
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            return

    async def _run(self) -> None:
        logger.info(
            "Attendance email worker started after_shift_minutes=%d scan_interval_seconds=%d",
            self.settings.attendance_email_after_shift_minutes,
            self.settings.attendance_email_scan_interval_seconds,
        )
        while True:
            try:
                AttendanceEmailService().process_due_notifications()
            except Exception as exc:
                logger.warning("Attendance email worker failed: %s", exc)
            await asyncio.sleep(max(10, self.settings.attendance_email_scan_interval_seconds))
