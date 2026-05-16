from pydantic import BaseModel, Field


class AttendanceRecognizeRequest(BaseModel):
    device_id: str = Field(min_length=2, max_length=120)
    cropped_image_base64: str = Field(min_length=10)


class AttendanceConfirmRequest(BaseModel):
    employee_id: int = Field(ge=1)
    device_id: str = Field(min_length=2, max_length=120)
    cropped_image_base64: str = Field(min_length=10)
    score: float = 0.0
    threshold: float = 0.0
    is_live: bool = True


class AttendanceLogItem(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    device_id: str
    action_type: str
    event_time: str
    score: float
    threshold: float
    is_live: bool
    snapshot_url: str | None
    status: str
    reason: str | None
    created_at: str


class AttendanceLogUpdateRequest(BaseModel):
    action_type: str | None = None
    status: str | None = None
    reason: str | None = None


class AnomalyReviewRequest(BaseModel):
    resolution_note: str = Field(min_length=1, max_length=1000)


class LeaveCalendarCreateRequest(BaseModel):
    employee_id: int | None = Field(default=None, ge=1)
    leave_date: str = Field(min_length=10, max_length=10)
    leave_type: str = Field(default="leave", min_length=2, max_length=80)
    reason: str = Field(default="", max_length=1000)
