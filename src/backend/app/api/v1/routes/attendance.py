from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.v1.dependencies import require_roles
from app.core.permissions import ROLE_ADMIN, ROLE_MANAGER
from app.schemas.attendance import AttendanceLogUpdateRequest, AttendanceRecognizeRequest
from app.schemas.common import build_success
from app.services.attendance_service import AttendanceService


router = APIRouter(prefix="/attendance", tags=["attendance"])
service = AttendanceService()


@router.post("/recognize")
def recognize_attendance(payload: AttendanceRecognizeRequest, _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    data = service.recognize_and_attend(payload.device_id, payload.cropped_image_base64)
    return build_success(data)


@router.post("/kiosk-checkin")
def kiosk_checkin(payload: AttendanceRecognizeRequest):
    data = service.recognize_and_attend(payload.device_id, payload.cropped_image_base64)
    return build_success(data)


@router.websocket("/kiosk-ws")
async def kiosk_websocket(websocket: WebSocket):
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

            data = service.recognize_and_attend(device_id, frame)
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
    current_user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER)),
):
    data = service.list_logs(
        employee_id=employee_id,
        date_from=date_from,
        date_to=date_to,
        status=status,
        action_type=action_type,
        device_id=device_id,
        current_user=current_user,
    )
    return build_success(data)


@router.get("/kiosk-logs")
def kiosk_logs(limit: int = 20):
    items = service.list_logs(
        employee_id=None,
        date_from=None,
        date_to=None,
        status=None,
        action_type=None,
        device_id=None,
        current_user=None,
    )
    limit = max(1, min(limit, 100))
    return build_success(items[:limit])


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
    data = service.update_log(log_id=log_id, payload=payload.model_dump(exclude_unset=True), current_user=current_user)
    return build_success(data)
