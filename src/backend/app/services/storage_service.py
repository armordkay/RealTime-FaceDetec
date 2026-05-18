import base64
import binascii
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class ImageStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def save_base64_image(self, image_base64: str, folder: str, prefix: str) -> str:
        image_bytes = self._decode_image(image_base64)
        object_name = f"{folder.strip('/')}/{prefix}_{uuid4().hex}.jpg"

        if self._minio_enabled():
            return self._save_to_minio(image_bytes, object_name)

        return self._save_to_local(image_bytes, object_name)

    def _decode_image(self, image_base64: str) -> bytes:
        raw = image_base64.strip()
        if "," in raw and raw.startswith("data:"):
            raw = raw.split(",", maxsplit=1)[1]

        try:
            return base64.b64decode(raw, validate=True)
        except binascii.Error as exc:
            raise ValueError("Invalid base64 image") from exc

    def _minio_enabled(self) -> bool:
        return bool(
            self.settings.minio_endpoint
            and self.settings.minio_access_key
            and self.settings.minio_secret_key
        )

    def _save_to_local(self, image_bytes: bytes, object_name: str) -> str:
        target = Path(self.settings.media_dir) / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image_bytes)
        return f"{self.settings.public_media_url.rstrip('/')}/{object_name}"

    def _save_to_minio(self, image_bytes: bytes, object_name: str) -> str:
        from minio import Minio

        client = Minio(
            self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure,
        )

        if not client.bucket_exists(self.settings.minio_bucket):
            client.make_bucket(self.settings.minio_bucket)

        client.put_object(
            self.settings.minio_bucket,
            object_name,
            BytesIO(image_bytes),
            length=len(image_bytes),
            content_type="image/jpeg",
        )

        public_base = self.settings.minio_public_url
        if public_base:
            return f"{public_base.rstrip('/')}/{self.settings.minio_bucket}/{object_name}"

        protocol = "https" if self.settings.minio_secure else "http"
        return f"{protocol}://{self.settings.minio_endpoint}/{self.settings.minio_bucket}/{object_name}"
