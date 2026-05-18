from pydantic import BaseModel, Field


class AdminUserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=120)
    role: str = Field(default="viewer")
    employee_id: int | None = None


class AdminUserUpdateRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    employee_id: int | None = None


class SystemConfigUpdateRequest(BaseModel):
    recognition_threshold: float = Field(ge=0.0, le=1.0)
    kiosk_allowed_devices: str = Field(default="", max_length=1000)
    anomaly_safe_score_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    anomaly_short_session_minutes: int = Field(default=15, ge=1, le=240)
    anomaly_near_event_minutes: int = Field(default=5, ge=1, le=60)
