import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")


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
    data_backend: str

    supabase_url: str | None
    supabase_key: str | None

    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int

    recognition_threshold: float
    anomaly_safe_score_threshold: float
    anomaly_short_session_minutes: int
    anomaly_near_event_minutes: int
    kiosk_api_key: str | None

    media_dir: str
    public_media_url: str

    minio_endpoint: str | None
    minio_access_key: str | None
    minio_secret_key: str | None
    minio_bucket: str
    minio_secure: bool
    minio_public_url: str | None

    alert_email_enabled: bool
    alert_smtp_host: str | None
    alert_smtp_port: int
    alert_smtp_username: str | None
    alert_smtp_password: str | None
    alert_smtp_from: str | None
    alert_email_recipients: list[str]
    alert_smtp_use_tls: bool

    attendance_email_enabled: bool
    attendance_email_after_shift_minutes: int
    attendance_email_scan_interval_seconds: int


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
        data_backend=os.getenv("DATA_BACKEND", "sqlite").strip().lower(),
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY"),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=_parse_int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"), 60
        ),
        recognition_threshold=_parse_float(os.getenv("RECOGNITION_THRESHOLD"), 0.65),
        anomaly_safe_score_threshold=_parse_float(os.getenv("ANOMALY_SAFE_SCORE_THRESHOLD"), 0.8),
        anomaly_short_session_minutes=_parse_int(os.getenv("ANOMALY_SHORT_SESSION_MINUTES"), 15),
        anomaly_near_event_minutes=_parse_int(os.getenv("ANOMALY_NEAR_EVENT_MINUTES"), 5),
        kiosk_api_key=os.getenv("KIOSK_API_KEY"),
        media_dir=os.getenv("MEDIA_DIR", "media"),
        public_media_url=os.getenv("PUBLIC_MEDIA_URL", "/media"),
        minio_endpoint=os.getenv("MINIO_ENDPOINT"),
        minio_access_key=os.getenv("MINIO_ACCESS_KEY"),
        minio_secret_key=os.getenv("MINIO_SECRET_KEY"),
        minio_bucket=os.getenv("MINIO_BUCKET", "face-attendance"),
        minio_secure=_parse_bool(os.getenv("MINIO_SECURE"), False),
        minio_public_url=os.getenv("MINIO_PUBLIC_URL"),
        alert_email_enabled=_parse_bool(os.getenv("ALERT_EMAIL_ENABLED"), False),
        alert_smtp_host=os.getenv("ALERT_SMTP_HOST"),
        alert_smtp_port=_parse_int(os.getenv("ALERT_SMTP_PORT"), 587),
        alert_smtp_username=os.getenv("ALERT_SMTP_USERNAME"),
        alert_smtp_password=os.getenv("ALERT_SMTP_PASSWORD"),
        alert_smtp_from=os.getenv("ALERT_SMTP_FROM"),
        alert_email_recipients=_parse_list(os.getenv("ALERT_EMAIL_RECIPIENTS"), []),
        alert_smtp_use_tls=_parse_bool(os.getenv("ALERT_SMTP_USE_TLS"), True),
        attendance_email_enabled=_parse_bool(os.getenv("ATTENDANCE_EMAIL_ENABLED"), False),
        attendance_email_after_shift_minutes=_parse_int(
            os.getenv("ATTENDANCE_EMAIL_AFTER_SHIFT_MINUTES")
            or os.getenv("ATTENDANCE_EMAIL_DELAY_MINUTES"),
            30,
        ),
        attendance_email_scan_interval_seconds=_parse_int(
            os.getenv("ATTENDANCE_EMAIL_SCAN_INTERVAL_SECONDS"),
            60,
        ),
    )
