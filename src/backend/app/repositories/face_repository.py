from sqlalchemy import func, select

from app.db.session import session_scope
from app.db.supabase_client import get_supabase_client, model_to_payload, row_to_model, supabase_enabled
from app.models.entities import FaceSample


class FaceRepository:
    def create_many(self, samples: list[FaceSample]) -> list[FaceSample]:
        if supabase_enabled():
            if not samples:
                return []
            rows = get_supabase_client().insert(
                "face_samples",
                [model_to_payload(sample, "face_samples") for sample in samples],
            )
            return [row_to_model(FaceSample, row, "face_samples") for row in rows]

        with session_scope() as db:
            db.add_all(samples)
            db.flush()
            for sample in samples:
                db.refresh(sample)
            return samples

    def list_by_employee(self, employee_id: int) -> list[FaceSample]:
        if supabase_enabled():
            rows = get_supabase_client().select(
                "face_samples",
                {"employee_id": f"eq.{employee_id}", "is_active": "eq.true", "order": "id.asc"},
            )
            return [row_to_model(FaceSample, row, "face_samples") for row in rows]

        with session_scope() as db:
            statement = (
                select(FaceSample)
                .where(FaceSample.employee_id == employee_id, FaceSample.is_active.is_(True))
                .order_by(FaceSample.id)
            )
            return list(db.scalars(statement))

    def list_active_with_embeddings(self) -> list[FaceSample]:
        if supabase_enabled():
            rows = get_supabase_client().select(
                "face_samples",
                {"is_active": "eq.true", "embedding": "not.is.null", "order": "employee_id.asc,id.asc"},
            )
            return [row_to_model(FaceSample, row, "face_samples") for row in rows]

        with session_scope() as db:
            statement = (
                select(FaceSample)
                .where(FaceSample.is_active.is_(True), FaceSample.embedding.is_not(None))
                .order_by(FaceSample.employee_id, FaceSample.id)
            )
            return list(db.scalars(statement))

    def count_by_employee(self, employee_id: int) -> int:
        if supabase_enabled():
            return len(self.list_by_employee(employee_id))

        with session_scope() as db:
            statement = select(func.count()).select_from(FaceSample).where(
                FaceSample.employee_id == employee_id,
                FaceSample.is_active.is_(True),
            )
            return int(db.scalar(statement) or 0)

    def count_by_employee_ids(self, employee_ids: list[int]) -> dict[int, int]:
        if not employee_ids:
            return {}

        if supabase_enabled():
            counts = dict.fromkeys(employee_ids, 0)
            rows = get_supabase_client().select(
                "face_samples",
                {"is_active": "eq.true", "employee_id": f"in.({','.join(str(item) for item in employee_ids)})"},
            )
            for sample in [row_to_model(FaceSample, row, "face_samples") for row in rows]:
                if sample.employee_id in counts:
                    counts[sample.employee_id] += 1
            return counts

        with session_scope() as db:
            statement = (
                select(FaceSample.employee_id, func.count())
                .where(
                    FaceSample.employee_id.in_(employee_ids),
                    FaceSample.is_active.is_(True),
                )
                .group_by(FaceSample.employee_id)
            )
            return {employee_id: int(count) for employee_id, count in db.execute(statement)}
