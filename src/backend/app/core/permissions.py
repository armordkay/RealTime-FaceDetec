from typing import Iterable

ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"
ROLE_VIEWER = "viewer"


def has_role(user_role: str, allowed_roles: Iterable[str]) -> bool:
    return user_role in set(allowed_roles)
