from datetime import datetime

from sqlalchemy import select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import AnomalyFlag, utc_now


class AnomalyFlagRepository:
    def create_many(self, flags: list[AnomalyFlag]) -> list[AnomalyFlag]:
        if not flags:
            return []

        if supabase_enabled():
            payload = [model_to_payload(flag, "anomaly_flags") for flag in flags]
            rows = get_supabase_client().insert("anomaly_flags", payload)
            return [row_to_model(AnomalyFlag, row, "anomaly_flags") for row in rows]

        with session_scope() as db:
            db.add_all(flags)
            db.flush()
            for flag in flags:
                db.refresh(flag)
            return flags

    def list(
        self,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
    ) -> list[AnomalyFlag]:
        if supabase_enabled():
            params: dict[str, str] = {"order": "created_at.desc"}
            if status:
                params["status"] = f"eq.{status}"
            if date_from and date_to:
                params["and"] = f"(created_at.gte.{date_from.isoformat()},created_at.lte.{date_to.isoformat()})"
            elif date_from:
                params["created_at"] = f"gte.{date_from.isoformat()}"
            elif date_to:
                params["created_at"] = f"lte.{date_to.isoformat()}"
            if limit is not None:
                params["limit"] = str(limit)
            return [
                row_to_model(AnomalyFlag, row, "anomaly_flags")
                for row in get_supabase_client().select("anomaly_flags", params)
            ]

        with session_scope() as db:
            statement = select(AnomalyFlag)
            if status:
                statement = statement.where(AnomalyFlag.status == status)
            if date_from:
                statement = statement.where(AnomalyFlag.created_at >= date_from)
            if date_to:
                statement = statement.where(AnomalyFlag.created_at <= date_to)
            statement = statement.order_by(AnomalyFlag.created_at.desc())
            if limit is not None:
                statement = statement.limit(limit)
            return list(db.scalars(statement))

    def get(self, flag_id: int) -> AnomalyFlag | None:
        if supabase_enabled():
            rows = get_supabase_client().select("anomaly_flags", {"id": f"eq.{flag_id}", "limit": "1"})
            return row_to_model(AnomalyFlag, rows[0], "anomaly_flags") if rows else None

        with session_scope() as db:
            return db.get(AnomalyFlag, flag_id)

    def update(self, flag: AnomalyFlag) -> AnomalyFlag:
        if supabase_enabled():
            rows = get_supabase_client().update(
                "anomaly_flags",
                {"id": f"eq.{flag.id}"},
                model_to_payload(flag, "anomaly_flags"),
            )
            return row_to_model(AnomalyFlag, rows[0], "anomaly_flags")

        with session_scope() as db:
            merged = db.merge(flag)
            db.flush()
            db.refresh(merged)
            return merged

    def mark_reviewed(self, flag_id: int, reviewer_user_id: int, note: str) -> AnomalyFlag | None:
        flag = self.get(flag_id)
        if flag is None:
            return None
        flag.status = "reviewed"
        flag.reviewed_at = utc_now()
        flag.reviewer_user_id = reviewer_user_id
        flag.resolution_note = note
        return self.update(flag)
