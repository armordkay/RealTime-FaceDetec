"""
Face Enrollment Service — DeepFace implementation
--------------------------------------------------
Khi enroll:
  1. Nhận list ảnh base64 từ frontend
  2. Dùng DeepFace (qua RecognitionService) trích xuất embedding thật
  3. Lưu embedding dạng JSON string vào cột `embedding` của FaceSample
  4. Lưu ảnh gốc vào storage (local hoặc MinIO) như cũ
"""

import json
import logging

from fastapi import HTTPException, status

from app.core.timezone import to_vietnam_iso
from app.models.entities import FaceSample, utc_now
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.face_repository import FaceRepository
from app.services.recognition_service import DEEPFACE_MODEL, EMBEDDING_VERSION, RecognitionService
from app.services.storage_service import ImageStorageService

logger = logging.getLogger(__name__)


class FaceEnrollmentService:
    def __init__(self) -> None:
        self.employee_repository = EmployeeRepository()
        self.face_repository = FaceRepository()
        self.storage_service = ImageStorageService()
        self.recognition_service = RecognitionService()

    def enroll(self, employee_id: int, samples: list[dict]) -> dict:
        """
        Enroll khuôn mặt cho nhân viên.

        Mỗi phần tử trong `samples` là dict có key `image_base64`.
        Với mỗi ảnh:
          - Trích xuất embedding bằng DeepFace
          - Lưu ảnh lên storage
          - Tạo FaceSample với embedding thật

        Trả về số lượng sample thành công và thất bại.
        """
        employee = self.employee_repository.get(employee_id)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        created_samples: list[FaceSample] = []
        failed_samples = 0
        failure_reasons: list[str] = []

        for idx, sample in enumerate(samples):
            image_base64 = sample.get("image_base64", "")

            if len(image_base64) < 20:
                failed_samples += 1
                failure_reasons.append(f"Sample {idx + 1}: image too short / empty")
                continue

            # --- Trích xuất embedding thật bằng DeepFace ---
            embedding = self.recognition_service.extract_embedding_from_base64(image_base64)
            if embedding is None:
                failed_samples += 1
                failure_reasons.append(f"Sample {idx + 1}: no face detected")
                logger.info(
                    "Enroll employee %d sample %d: face not detected, skipping",
                    employee_id, idx + 1,
                )
                continue

            # --- Lưu ảnh lên storage ---
            try:
                image_url = self.storage_service.save_base64_image(
                    image_base64,
                    folder=f"faces/employee_{employee_id}",
                    prefix="face",
                )
            except ValueError as exc:
                failed_samples += 1
                failure_reasons.append(f"Sample {idx + 1}: storage error ({exc})")
                continue

            # --- Tính quality score đơn giản từ norm của embedding ---
            # Embedding đã chuẩn hóa bởi DeepFace, norm ≈ 1 nên dùng
            # độ phân tán (std) của vector để ước lượng chất lượng.
            import numpy as np
            emb_array = np.array(embedding, dtype=np.float32)
            quality_score = float(np.clip(np.std(emb_array) * 10, 0.5, 0.99))

            created_samples.append(
                FaceSample(
                    employee_id=employee_id,
                    cropped_face_url=image_url,
                    quality_score=round(quality_score, 4),
                    model_name=DEEPFACE_MODEL,
                    embedding_version=EMBEDDING_VERSION,
                    embedding=json.dumps(embedding),   # lưu dạng JSON string
                    is_active=True,
                    created_at=utc_now(),
                )
            )

        self.face_repository.create_many(created_samples)

        logger.info(
            "Enroll employee %d: %d saved, %d failed",
            employee_id, len(created_samples), failed_samples,
        )

        result = {
            "employee_id": employee_id,
            "saved_samples": len(created_samples),
            "failed_samples": failed_samples,
            "message": (
                "Enrollment completed"
                if created_samples
                else "No face samples were saved"
            ),
        }

        # Đính kèm lý do thất bại để frontend hiển thị (nếu có)
        if failure_reasons:
            result["failure_reasons"] = failure_reasons

        return result

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
                "has_embedding": item.embedding is not None,  # không expose vector ra ngoài
                "is_active": item.is_active,
                "created_at": to_vietnam_iso(item.created_at),
            }
            for item in samples
        ]
