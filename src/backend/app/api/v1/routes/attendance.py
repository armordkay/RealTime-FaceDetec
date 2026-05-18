from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.api.v1.dependencies import require_roles
from app.core.config import get_settings
from app.core.permissions import ROLE_ADMIN, ROLE_MANAGER
from app.schemas.attendance import (
    AnomalyReviewRequest,
    AttendanceConfirmRequest,
    AttendanceLogUpdateRequest,
    AttendanceRecognizeRequest,
    LeaveCalendarCreateRequest,
)
from app.schemas.common import build_success
from app.services.anomaly_service import AnomalyService
from app.services.attendance_service import AttendanceService
from app.services.leave_calendar_service import LeaveCalendarService


router = APIRouter(prefix="/attendance", tags=["attendance"])
service = AttendanceService()
anomaly_service = AnomalyService()
leave_service = LeaveCalendarService()
settings = get_settings()


def verify_kiosk_request(request: Request) -> None:
    if not settings.kiosk_api_key:
        return

    provided_key = request.headers.get("X-Kiosk-Key") or request.query_params.get("kiosk_key")
    if provided_key != settings.kiosk_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid kiosk key")


def websocket_has_valid_kiosk_key(websocket: WebSocket) -> bool:
    if not settings.kiosk_api_key:
        return True
    return websocket.query_params.get("kiosk_key") == settings.kiosk_api_key


@router.post("/recognize")
def recognize_attendance(payload: AttendanceRecognizeRequest, _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    data = service.recognize_and_attend(payload.device_id, payload.cropped_image_base64)
    return build_success(data)


@router.post("/kiosk-checkin")
def kiosk_checkin(payload: AttendanceRecognizeRequest, _: None = Depends(verify_kiosk_request)):
    data = service.recognize_and_attend(payload.device_id, payload.cropped_image_base64)
    return build_success(data)


@router.post("/kiosk-confirm")
def kiosk_confirm(payload: AttendanceConfirmRequest, _: None = Depends(verify_kiosk_request)):
    data = service.confirm_attendance(
        employee_id=payload.employee_id,
        device_id=payload.device_id,
        cropped_image_base64=payload.cropped_image_base64,
        score=payload.score,
        threshold=payload.threshold,
        is_live=payload.is_live,
    )
    return build_success(data)


@router.websocket("/kiosk-ws")
async def kiosk_websocket(websocket: WebSocket):
    if not websocket_has_valid_kiosk_key(websocket):
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            device_id = payload.get("device_id")
            frame = payload.get("cropped_image_base64")

            if not isinstance(device_id, str) or not isinstance(frame, str):
                await websocket.send_json(
                    {
                        "success": False,
                        "error": {
                            "code": "INVALID_PAYLOAD",
                            "message": "device_id and cropped_image_base64 are required",
                        },
                    }
                )
                continue

            data = service.recognize_for_attendance(device_id, frame)
            await websocket.send_json(build_success(data))
    except WebSocketDisconnect:
        return


@router.get("/logs")
def attendance_logs(
    employee_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    action_type: str | None = None,
    device_id: str | None = None,
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = service.list_logs(
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        action_type=action_type,
        device_id=device_id,
    )
    return build_success(data)


@router.get("/kiosk-logs")
def kiosk_logs(limit: int = 20, _: None = Depends(verify_kiosk_request)):
    limit = max(1, min(limit, 100))
    items = service.list_logs(
        employee_id=None,
        date_from=None,
        date_to=None,
        status=None,
        action_type=None,
        device_id=None,
        limit=limit,
    )
    return build_success(items)


@router.get("/my-logs")
def my_logs(current_user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    employee_id = current_user.get("employee_id")
    if employee_id is None:
        return build_success([])
    data = service.my_logs(employee_id)
    return build_success(data)


@router.get("/my-status")
def my_status(current_user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    employee_id = current_user.get("employee_id")
    if employee_id is None:
        return build_success(
            {
                "employee_id": None,
                "employee_name": "Unlinked account",
                "date": None,
                "check_in_count": 0,
                "check_out_count": 0,
                "last_action": None,
                "last_status": None,
                "last_event_time": None,
                "next_expected_action": None,
            }
        )
    data = service.my_status(employee_id)
    return build_success(data)


@router.patch("/logs/{log_id}")
def update_attendance_log(
    log_id: int,
    payload: AttendanceLogUpdateRequest,
    current_user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = service.update_log(
        log_id=log_id,
        payload=payload.model_dump(exclude_unset=True),
        actor_user=current_user,
    )
    return build_success(data)


@router.get("/logs/{log_id}/audit")
def attendance_log_audit(
    log_id: int,
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = service.list_audit_logs(log_id)
    return build_success(data)


@router.get("/anomalies")
def list_anomalies(
    status: str | None = "open",
    today_only: bool = True,
    limit: int = 100,
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = anomaly_service.list_flags(status=status, today_only=today_only, limit=limit)
    return build_success(data)


@router.patch("/anomalies/{flag_id}/review")
def review_anomaly(
    flag_id: int,
    payload: AnomalyReviewRequest,
    current_user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = anomaly_service.mark_reviewed(
        flag_id=flag_id,
        reviewer_user_id=current_user["id"],
        note=payload.resolution_note,
    )
    return build_success(data)


@router.get("/leave-calendar")
def list_leave_calendar(
    leave_date: str,
    _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = leave_service.list_by_date(leave_date)
    return build_success(data)


@router.post("/leave-calendar")
def create_leave_calendar(
    payload: LeaveCalendarCreateRequest,
    current_user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = leave_service.create(payload.model_dump(), current_user)
    return build_success(data)
