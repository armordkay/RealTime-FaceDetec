from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Keep imports here when SQLAlchemy models are added.
# from app.models.user import User
# from app.models.employee import Employee
# from app.models.shift import Shift
