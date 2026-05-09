from sqlalchemy import select

from app.db.session import session_scope
from app.models.entities import Shift


class ShiftRepository:
    def list(self) -> list[Shift]:
        with session_scope() as db:
            return list(db.scalars(select(Shift).order_by(Shift.id)))

    def get(self, shift_id: int) -> Shift | None:
        with session_scope() as db:
            return db.get(Shift, shift_id)

    def create(self, shift: Shift) -> Shift:
        with session_scope() as db:
            db.add(shift)
            db.flush()
            db.refresh(shift)
            return shift

    def update(self, shift: Shift) -> Shift:
        with session_scope() as db:
            merged = db.merge(shift)
            db.flush()
            db.refresh(merged)
            return merged

    def delete(self, shift_id: int) -> bool:
        with session_scope() as db:
            shift = db.get(Shift, shift_id)
            if shift is None:
                return False
            db.delete(shift)
            return True
