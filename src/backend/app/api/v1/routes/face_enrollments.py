from fastapi import APIRouter, Depends

from app.api.v1.dependencies import require_roles
from app.core.permissions import ROLE_ADMIN, ROLE_MANAGER
from app.schemas.common import build_success
from app.schemas.face_enrollment import FaceEnrollmentRequest
from app.services.face_enrollment_service import FaceEnrollmentService


router = APIRouter(prefix="/face-enrollments", tags=["face-enrollments"])
service = FaceEnrollmentService()


@router.post("")
def enroll_face(payload: FaceEnrollmentRequest, _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    data = service.enroll(employee_id=payload.employee_id, samples=[item.model_dump() for item in payload.samples])
    return build_success(data)


@router.get("/employees/{employee_id}/face-samples")
def list_face_samples(employee_id: int, _: dict = Depends(require_roles(ROLE_ADMIN, ROLE_MANAGER))):
    data = service.list_samples(employee_id)
    return build_success(data)
