from sqlalchemy import select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import Shift


class ShiftRepository:
    def list(self) -> list[Shift]:
        if supabase_enabled():
            rows = get_supabase_client().select("shifts", {"order": "id.asc"})
            return [row_to_model(Shift, row, "shifts") for row in rows]

        with session_scope() as db:
            return list(db.scalars(select(Shift).order_by(Shift.id)))

    def get(self, shift_id: int) -> Shift | None:
        if supabase_enabled():
            rows = get_supabase_client().select("shifts", {"id": f"eq.{shift_id}", "limit": "1"})
            return row_to_model(Shift, rows[0], "shifts") if rows else None

        with session_scope() as db:
            return db.get(Shift, shift_id)

    def create(self, shift: Shift) -> Shift:
        if supabase_enabled():
            rows = get_supabase_client().insert("shifts", model_to_payload(shift, "shifts"))
            return row_to_model(Shift, rows[0], "shifts")

        with session_scope() as db:
            db.add(shift)
            db.flush()
            db.refresh(shift)
            return shift

    def update(self, shift: Shift) -> Shift:
        if supabase_enabled():
            rows = get_supabase_client().update(
                "shifts",
                {"id": f"eq.{shift.id}"},
                model_to_payload(shift, "shifts"),
            )
            return row_to_model(Shift, rows[0], "shifts")

        with session_scope() as db:
            merged = db.merge(shift)
            db.flush()
            db.refresh(merged)
            return merged

    def delete(self, shift_id: int) -> bool:
        if supabase_enabled():
            return get_supabase_client().delete("shifts", {"id": f"eq.{shift_id}"})

        with session_scope() as db:
            shift = db.get(Shift, shift_id)
            if shift is None:
                return False
            db.delete(shift)
            return True
