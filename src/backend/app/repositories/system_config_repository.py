from sqlalchemy import select

from app.db.session import session_scope
from app.models.entities import SystemConfig, utc_now


class SystemConfigRepository:
    def list(self) -> list[SystemConfig]:
        with session_scope() as db:
            return list(db.scalars(select(SystemConfig).order_by(SystemConfig.key)))

    def get(self, key: str) -> SystemConfig | None:
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
