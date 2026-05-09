from fastapi import HTTPException, status

from app.core.timezone import to_vietnam_iso
from app.models.entities import FaceSample, utc_now
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.face_repository import FaceRepository
from app.services.storage_service import ImageStorageService


class FaceEnrollmentService:
    def __init__(self) -> None:
        self.employee_repository = EmployeeRepository()
        self.face_repository = FaceRepository()
        self.storage_service = ImageStorageService()

    def enroll(self, employee_id: int, samples: list[dict]) -> dict:
        employee = self.employee_repository.get(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        created_samples: list[FaceSample] = []
        failed_samples = 0

        for idx, sample in enumerate(samples):
            image_base64 = sample["image_base64"]
            if len(image_base64) < 20:
                failed_samples += 1
                continue

            try:
                image_url = self.storage_service.save_base64_image(
                    image_base64,
                    folder=f"faces/employee_{employee_id}",
                    prefix="face",
                )
            except ValueError:
                failed_samples += 1
                continue

            quality_score = min(0.95, 0.70 + (idx * 0.03))
            created_samples.append(
                FaceSample(
                    employee_id=employee_id,
                    cropped_face_url=image_url,
                    quality_score=quality_score,
                    model_name="mock-face-model",
                    embedding_version="v0-mock",
                    is_active=True,
                    created_at=utc_now(),
                )
            )

        self.face_repository.create_many(created_samples)

        return {
            "employee_id": employee_id,
            "saved_samples": len(created_samples),
            "failed_samples": failed_samples,
            "message": "Enrollment completed",
        }

    def list_samples(self, employee_id: int) -> list[dict]:
        employee = self.employee_repository.get(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        samples = self.face_repository.list_by_employee(employee_id)
        return [
            {
                "id": item.id,
                "employee_id": item.employee_id,
                "cropped_face_url": item.cropped_face_url,
                "quality_score": item.quality_score,
                "model_name": item.model_name,
                "embedding_version": item.embedding_version,
                "is_active": item.is_active,
                "created_at": to_vietnam_iso(item.created_at),
            }
            for item in samples
        ]
