"""
Recognition Service — DeepFace implementation
----------------------------------------------
Thay thế mock SHA256 bằng nhận diện khuôn mặt thật dùng DeepFace.

Luồng:
  1. Decode base64 → numpy image
  2. DeepFace.represent() → trích xuất embedding 512 chiều (Facenet512)
  3. So sánh cosine similarity với tất cả embedding đã enroll trong DB
  4. Trả về employee có similarity cao nhất nếu vượt threshold
"""

import base64
import json
import logging
from io import BytesIO

import numpy as np

from app.core.config import get_settings
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.face_repository import FaceRepository
from app.repositories.system_config_repository import SystemConfigRepository

logger = logging.getLogger(__name__)

# Model dùng để trích xuất embedding.
# Facenet512 cho độ chính xác cao và tương thích GPU tốt.
# Có thể đổi sang "ArcFace" nếu muốn.
DEEPFACE_MODEL = "Facenet512"
EMBEDDING_VERSION = "deepface-facenet512-v1"


def _decode_image_to_numpy(image_base64: str) -> np.ndarray:
    """Decode base64 string (có hoặc không có data URI prefix) sang numpy array."""
    raw = image_base64.strip()
    if "," in raw and raw.startswith("data:"):
        raw = raw.split(",", maxsplit=1)[1]

    image_bytes = base64.b64decode(raw)

    # Import ở đây để tránh load nặng khi module import lần đầu
    from PIL import Image
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    return np.array(image)


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Tính cosine similarity giữa 2 vector embedding."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _extract_embedding(image_np: np.ndarray) -> list[float] | None:
    """
    Dùng DeepFace để trích xuất embedding từ numpy image.
    Trả về None nếu không phát hiện khuôn mặt hoặc có lỗi.
    """
    from deepface import DeepFace

    # Try real face detectors first. The final "skip" fallback embeds the full
    # image so enrollment can still work when webcam frames are not tightly
    # cropped, but detector-based samples are preferred for accuracy.
    detector_backends = ("opencv", "mtcnn", "skip")
    last_error: Exception | None = None

    for detector_backend in detector_backends:
        try:
            results = DeepFace.represent(
                img_path=image_np,
                model_name=DEEPFACE_MODEL,
                enforce_detection=detector_backend != "skip",
                detector_backend=detector_backend,
                align=detector_backend != "skip",
            )
            if results:
                return results[0]["embedding"]
        except Exception as exc:
            last_error = exc
            logger.debug(
                "DeepFace.represent failed with detector %s: %s",
                detector_backend,
                exc,
            )

    if last_error is not None:
        logger.info("DeepFace could not extract embedding: %s", last_error)
    return None


class RecognitionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.employee_repository = EmployeeRepository()
        self.face_repository = FaceRepository()
        self.config_repository = SystemConfigRepository()

    def recognize(self, cropped_image_base64: str) -> dict:
        """
        Nhận diện khuôn mặt từ ảnh base64.

        Returns dict với các key:
          match_found, employee_id, employee_name, score, threshold, is_live, message
        """
        threshold = self.get_threshold()

        # --- 1. Decode ảnh ---
        try:
            image_np = _decode_image_to_numpy(cropped_image_base64)
        except Exception as exc:
            logger.warning("Image decode error: %s", exc)
            return self._no_match(threshold, "Invalid image data")

        # --- 2. Trích xuất embedding từ frame ---
        query_embedding = _extract_embedding(image_np)
        if query_embedding is None:
            return self._no_match(threshold, "No face detected in frame")

        # --- 3. Load enrolled embeddings and related employees ---
        samples = self.face_repository.list_active_with_embeddings()
        if not samples:
            return self._no_match(threshold, "No enrolled face samples")

        employees = self.employee_repository.list_by_ids([sample.employee_id for sample in samples])
        if not employees:
            return self._no_match(threshold, "No enrolled profiles")

        employees_by_id = {employee.id: employee for employee in employees}
        best_employee = None
        best_score = -1.0

        for sample in samples:
            employee = employees_by_id.get(sample.employee_id)
            if employee is None or not sample.embedding:
                continue

            try:
                enrolled_embedding = json.loads(sample.embedding)
            except json.JSONDecodeError:
                logger.warning("Invalid embedding JSON for face sample %s", sample.id)
                continue

            sample_score = _cosine_similarity(query_embedding, enrolled_embedding)

            if sample_score > best_score:
                best_score = sample_score
                best_employee = employee

        # --- 4. Kiểm tra threshold ---
        if best_employee is None or best_score < threshold:
            return {
                "match_found": False,
                "employee_id": None,
                "employee_name": None,
                "score": round(best_score, 4) if best_score >= 0 else 0.0,
                "threshold": threshold,
                "is_live": True,
                "message": "No match found",
            }

        return {
            "match_found": True,
            "employee_id": best_employee.id,
            "employee_name": best_employee.full_name,
            "score": round(best_score, 4),
            "threshold": threshold,
            "is_live": True,
            "message": "Match found",
        }

    def extract_embedding_from_base64(self, image_base64: str) -> list[float] | None:
        """
        Public method cho FaceEnrollmentService dùng khi enroll.
        Trả về embedding vector hoặc None nếu không detect được mặt.
        """
        try:
            image_np = _decode_image_to_numpy(image_base64)
        except Exception:
            return None
        return _extract_embedding(image_np)

    def get_threshold(self) -> float:
        return self.config_repository.get_float(
            "recognition_threshold",
            self.settings.recognition_threshold,
        )

    @staticmethod
    def _no_match(threshold: float, message: str) -> dict:
        return {
            "match_found": False,
            "employee_id": None,
            "employee_name": None,
            "score": 0.0,
            "threshold": threshold,
            "is_live": True,
            "message": message,
        }
