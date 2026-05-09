from sqlalchemy import or_, select

from app.db.session import session_scope
from app.models.entities import User, utc_now


class UserRepository:
    def list(self) -> list[User]:
        with session_scope() as db:
            return list(db.scalars(select(User).order_by(User.id)))

    def find_by_username_or_email(self, credential: str) -> User | None:
        lookup = credential.strip().lower()
        with session_scope() as db:
            statement = select(User).where(
                or_(
                    User.username == lookup,
                    User.email == lookup,
                )
            )
            return db.scalar(statement)

    def get_by_id(self, user_id: int) -> User | None:
        with session_scope() as db:
            return db.get(User, user_id)

    def create(self, user: User) -> User:
        with session_scope() as db:
            db.add(user)
            db.flush()
            db.refresh(user)
            return user

    def update(self, user: User) -> User:
        user.updated_at = utc_now()
        with session_scope() as db:
            merged = db.merge(user)
            db.flush()
            db.refresh(merged)
            return merged

    def exists_by_username_or_email(self, username: str, email: str, ignore_id: int | None = None) -> bool:
        username_lookup = username.strip().lower()
        email_lookup = email.strip().lower()
        with session_scope() as db:
            records = db.scalars(select(User)).all()
            for user in records:
                if ignore_id is not None and user.id == ignore_id:
                    continue
                if user.username.lower() == username_lookup or user.email.lower() == email_lookup:
                    return True
            return False
