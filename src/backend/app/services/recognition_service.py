import hashlib

from app.core.config import get_settings
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.face_repository import FaceRepository
from app.repositories.system_config_repository import SystemConfigRepository


class RecognitionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.employee_repository = EmployeeRepository()
        self.face_repository = FaceRepository()
        self.config_repository = SystemConfigRepository()

    def recognize(self, device_id: str, cropped_image_base64: str) -> dict:
        samples = []
        employees = self.employee_repository.list()
        for employee in employees:
            emp_samples = self.face_repository.list_by_employee(employee.id)
            if emp_samples:
                samples.append((employee, emp_samples))

        if not samples:
            threshold = self.get_threshold()
            return {
                "match_found": False,
                "employee_id": None,
                "employee_name": None,
                "score": 0.0,
                "threshold": threshold,
                "is_live": True,
                "message": "No enrolled profiles",
            }

        # Mock recognition without AI model:
        # choose a candidate deterministically from frame hash so repeated frames
        # usually map to same person, while different people/angles can vary.
        frame_text = cropped_image_base64.strip()
        digest = hashlib.sha256(frame_text.encode("utf-8")).digest()
        picked_index = int.from_bytes(digest[:4], "big") % len(samples)
        employee = samples[picked_index][0]
        score = 0.72 + (digest[4] / 255.0) * 0.24
        threshold = self.get_threshold()

        if score < threshold:
            return {
                "match_found": False,
                "employee_id": None,
                "employee_name": None,
                "score": score,
                "threshold": threshold,
                "is_live": True,
                "message": "No match found",
            }

        return {
            "match_found": True,
            "employee_id": employee.id,
            "employee_name": employee.full_name,
            "score": score,
            "threshold": threshold,
            "is_live": True,
            "message": "Match found",
        }

    def get_threshold(self) -> float:
        return self.config_repository.get_float(
            "recognition_threshold",
            self.settings.recognition_threshold,
        )
