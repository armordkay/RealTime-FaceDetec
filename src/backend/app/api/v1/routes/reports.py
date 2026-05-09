from fastapi import APIRouter, Depends, Response

from app.api.v1.dependencies import require_roles
from app.core.permissions import ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER
from app.schemas.common import build_success
from app.services.report_service import ReportService


router = APIRouter(prefix="/reports", tags=["reports"])
service = ReportService()


@router.get("/attendance-daily")
def attendance_daily(date: str | None = None, _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER))):
    data = service.attendance_daily(date)
    return build_success(data)


@router.get("/attendance-monthly")
def attendance_monthly(month: str | None = None, _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER))):
    data = service.attendance_monthly(month)
    return build_success(data)


@router.get("/late-employees")
def late_employees(_: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER))):
    data = service.late_employees()
    return build_success(data)


@router.get("/export")
def export_report(format: str = "csv", _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER, ROLE_VIEWER))):
    if format != "csv":
        return build_success({"message": "Only csv is supported in MVP"})

    csv_data = service.export_csv()
    headers = {"Content-Disposition": 'attachment; filename="attendance_report.csv"'}
    return Response(content=csv_data, media_type="text/csv", headers=headers)
