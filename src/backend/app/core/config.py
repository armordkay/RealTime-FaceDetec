import os
from dataclasses import dataclass
from functools import lru_cache


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _parse_list(value: str | None, default: list[str]) -> list[str]:
    if value is None or not value.strip():
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    app_env: str
    debug: bool

    api_v1_prefix: str
    cors_origins: list[str]

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    recognition_threshold: float
    attendance_cooldown_seconds: int

    media_dir: str
    public_media_url: str

    minio_endpoint: str | None
    minio_access_key: str | None
    minio_secret_key: str | None
    minio_bucket: str
    minio_secure: bool
    minio_public_url: str | None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Face Attendance API"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        app_env=os.getenv("APP_ENV", "dev"),
        debug=_parse_bool(os.getenv("DEBUG"), True),
        api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
        cors_origins=_parse_list(
            os.getenv("CORS_ORIGINS"),
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        ),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./face_attendance.db"),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=_parse_int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"), 60
        ),
        recognition_threshold=_parse_float(os.getenv("RECOGNITION_THRESHOLD"), 0.65),
        attendance_cooldown_seconds=_parse_int(
            os.getenv("ATTENDANCE_COOLDOWN_SECONDS"), 60
        ),
        media_dir=os.getenv("MEDIA_DIR", "media"),
        public_media_url=os.getenv("PUBLIC_MEDIA_URL", "/media"),
        minio_endpoint=os.getenv("MINIO_ENDPOINT"),
        minio_access_key=os.getenv("MINIO_ACCESS_KEY"),
        minio_secret_key=os.getenv("MINIO_SECRET_KEY"),
        minio_bucket=os.getenv("MINIO_BUCKET", "face-attendance"),
        minio_secure=_parse_bool(os.getenv("MINIO_SECURE"), False),
        minio_public_url=os.getenv("MINIO_PUBLIC_URL"),
    )
