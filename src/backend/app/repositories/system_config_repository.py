from sqlalchemy import select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import SystemConfig, utc_now


class SystemConfigRepository:
    def list(self) -> list[SystemConfig]:
        if supabase_enabled():
            rows = get_supabase_client().select("system_configs", {"order": "key.asc"})
            return [row_to_model(SystemConfig, row, "system_configs") for row in rows]

        with session_scope() as db:
            return list(db.scalars(select(SystemConfig).order_by(SystemConfig.key)))

    def get(self, key: str) -> SystemConfig | None:
        if supabase_enabled():
            rows = get_supabase_client().select("system_configs", {"key": f"eq.{key}", "limit": "1"})
            return row_to_model(SystemConfig, rows[0], "system_configs") if rows else None

        with session_scope() as db:
            return db.get(SystemConfig, key)

    def get_value(self, key: str, default: str) -> str:
        item = self.get(key)
        return item.value if item else default

    def get_int(self, key: str, default: int) -> int:
        try:
            return int(self.get_value(key, str(default)))
        except ValueError:
            return default

    def get_float(self, key: str, default: float) -> float:
        try:
            return float(self.get_value(key, str(default)))
        except ValueError:
            return default

    def upsert(self, key: str, value: str, description: str = "") -> SystemConfig:
        if supabase_enabled():
            existing = self.get(key)
            item = SystemConfig(
                key=key,
                value=value,
                description=description or (existing.description if existing else ""),
                updated_at=utc_now(),
            )
            if existing is None:
                rows = get_supabase_client().insert("system_configs", model_to_payload(item, "system_configs", include_id=True))
            else:
                rows = get_supabase_client().update(
                    "system_configs",
                    {"key": f"eq.{key}"},
                    model_to_payload(item, "system_configs", include_id=True),
                )
            return row_to_model(SystemConfig, rows[0], "system_configs")

        with session_scope() as db:
            item = db.get(SystemConfig, key)
            if item is None:
                item = SystemConfig(
                    key=key,
                    value=value,
                    description=description,
                    updated_at=utc_now(),
                )
                db.add(item)
            else:
                item.value = value
                if description:
                    item.description = description
                item.updated_at = utc_now()

            db.flush()
            db.refresh(item)
            return item
