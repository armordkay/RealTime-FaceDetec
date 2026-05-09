from pydantic import BaseModel, Field


class FaceSampleInput(BaseModel):
    image_base64: str = Field(min_length=10)


class FaceEnrollmentRequest(BaseModel):
    employee_id: int
    samples: list[FaceSampleInput] = Field(min_length=1, max_length=10)


class FaceSampleItem(BaseModel):
    id: int
    employee_id: int
    cropped_face_url: str
    quality_score: float
    model_name: str
    embedding_version: str
    is_active: bool
    created_at: str
