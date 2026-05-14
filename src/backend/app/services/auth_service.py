from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.user_repository = UserRepository()

    def login(self, username: str, password: str, requested_role: str | None = None) -> dict:
        user = self.user_repository.find_by_username_or_email(username)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if requested_role and requested_role != user.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account does not belong to '{requested_role}' role",
            )

        access_token = create_access_token(
            payload={"sub": str(user.id), "role": user.role},
            secret_key=self.settings.jwt_secret_key,
            expires_minutes=self.settings.access_token_expire_minutes,
            algorithm=self.settings.jwt_algorithm,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "employee_id": user.employee_id,
            },
        }

    def get_me(self, user_id: int) -> dict:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "employee_id": user.employee_id,
        }

    def change_password(self, user_id: int, old_password: str, new_password: str) -> dict:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(old_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        self.user_repository.update(user)

        return {"message": "Password changed successfully"}
