"""Authentication and authorization helpers."""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from copilot.infrastructure.config.settings import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLES = {"admin", "hiring_manager", "hr_recruiter"}


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd_context.verify(password, hashed)


def create_access_token(user_id: UUID, role: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.algorithm)


def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.algorithm])
    except JWTError:
        return None


def require_role(role: str, allowed: set[str]) -> None:
    if role not in allowed:
        raise PermissionError(f"Role '{role}' not in {allowed}")
