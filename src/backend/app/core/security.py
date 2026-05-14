import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


def _urlsafe_b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(raw: str) -> bytes:
    padded = raw + "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{_urlsafe_b64encode(salt)}:{_urlsafe_b64encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt_b64, digest_b64 = password_hash.split(":", maxsplit=1)
        salt = _urlsafe_b64decode(salt_b64)
        expected = _urlsafe_b64decode(digest_b64)
    except Exception:
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(candidate, expected)


def create_access_token(
    payload: dict[str, Any],
    secret_key: str,
    expires_minutes: int,
    algorithm: str = "HS256",
) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    token_payload = {**payload, "exp": exp}
    return jwt.encode(token_payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, secret_key: str, algorithm: str = "HS256") -> dict[str, Any] | None:
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.PyJWTError:
        return None
