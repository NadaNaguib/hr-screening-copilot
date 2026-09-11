"""Authentication and authorization helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from copilot.infrastructure.config.settings import get_settings

ROLES = {"admin", "hiring_manager", "hr_recruiter"}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    pw = password.encode("utf-8")[:72]
    return bcrypt.checkpw(pw, hashed.encode("utf-8"))


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
