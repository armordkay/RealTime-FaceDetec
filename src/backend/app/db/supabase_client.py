from datetime import datetime
from typing import Any, TypeVar

import requests

from app.core.config import get_settings
from app.models.entities import AttendanceLog, Employee, FaceSample, Shift, SystemConfig, User


ModelT = TypeVar("ModelT")

TABLE_DATETIME_FIELDS = {
    "users": {"created_at", "updated_at"},
    "shifts": {"created_at"},
    "employees": {"created_at", "updated_at"},
    "face_samples": {"created_at"},
    "attendance_logs": {"event_time", "created_at"},
    "system_configs": {"updated_at"},
}


def supabase_enabled() -> bool:
    return get_settings().data_backend == "supabase"


def _parse_datetime(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return value


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def row_to_model(model_cls: type[ModelT], row: dict[str, Any], table: str) -> ModelT:
    values = dict(row)
    for field in TABLE_DATETIME_FIELDS.get(table, set()):
        if field in values:
            values[field] = _parse_datetime(values[field])
    return model_cls(**values)


def model_to_payload(model: Any, table: str, include_id: bool = False) -> dict[str, Any]:
    columns = model.__table__.columns.keys()
    payload: dict[str, Any] = {}
    for column in columns:
        if column == "id" and not include_id:
            continue
        value = getattr(model, column)
        if value is not None:
            payload[column] = _serialize_value(value)
    return payload


class SupabaseRestClient:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required when DATA_BACKEND=supabase")

        self.base_url = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": settings.supabase_key,
            "Authorization": f"Bearer {settings.supabase_key}",
            "Content-Type": "application/json",
        }

    def select(self, table: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/rest/v1/{table}",
            headers=self.headers,
            params={"select": "*", **(params or {})},
            timeout=30,
        )
        return self._json(response)

    def insert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        headers = {**self.headers, "Prefer": "return=representation"}
        response = requests.post(
            f"{self.base_url}/rest/v1/{table}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        return self._json(response)

    def update(self, table: str, filters: dict[str, str], payload: dict[str, Any]) -> list[dict[str, Any]]:
        headers = {**self.headers, "Prefer": "return=representation"}
        response = requests.patch(
            f"{self.base_url}/rest/v1/{table}",
            headers=headers,
            params=filters,
            json=payload,
            timeout=30,
        )
        return self._json(response)

    def delete(self, table: str, filters: dict[str, str]) -> bool:
        response = requests.delete(
            f"{self.base_url}/rest/v1/{table}",
            headers=self.headers,
            params=filters,
            timeout=30,
        )
        self._raise_for_status(response)
        return True

    def _json(self, response: requests.Response) -> list[dict[str, Any]]:
        self._raise_for_status(response)
        if not response.content:
            return []
        data = response.json()
        return data if isinstance(data, list) else [data]

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.ok:
            return
        raise RuntimeError(f"Supabase request failed: {response.status_code} {response.text}")


def get_supabase_client() -> SupabaseRestClient:
    return SupabaseRestClient()


MODEL_TABLES = {
    User: "users",
    Shift: "shifts",
    Employee: "employees",
    FaceSample: "face_samples",
    AttendanceLog: "attendance_logs",
    SystemConfig: "system_configs",
}
