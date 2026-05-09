from sqlalchemy import func, select

from app.db.session import session_scope
from app.models.entities import FaceSample


class FaceRepository:
    def create_many(self, samples: list[FaceSample]) -> list[FaceSample]:
        with session_scope() as db:
            db.add_all(samples)
            db.flush()
            for sample in samples:
                db.refresh(sample)
            return samples

    def list_by_employee(self, employee_id: int) -> list[FaceSample]:
        with session_scope() as db:
            statement = (
                select(FaceSample)
                .where(FaceSample.employee_id == employee_id, FaceSample.is_active.is_(True))
                .order_by(FaceSample.id)
            )
            return list(db.scalars(statement))

    def count_by_employee(self, employee_id: int) -> int:
        with session_scope() as db:
            statement = select(func.count()).select_from(FaceSample).where(
                FaceSample.employee_id == employee_id,
                FaceSample.is_active.is_(True),
            )
            return int(db.scalar(statement) or 0)
