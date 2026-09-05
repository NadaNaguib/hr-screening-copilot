"""FastAPI dependencies."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from copilot.infrastructure.auth.service import decode_token, require_role
from copilot.infrastructure.db.session import get_session as _get_session
from copilot.infrastructure.di import Container

security = HTTPBearer(auto_error=False)


async def get_session() -> AsyncGenerator:
    async for session in _get_session():
        yield session


async def get_container(session=Depends(get_session)) -> Container:
    return Container.from_session(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "missing_token", "message": "Authorization header required"},
        )
    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "invalid_token", "message": "Invalid or expired token"},
        )
    return {
        "id": UUID(payload["sub"]),
        "role": payload["role"],
        "email": payload.get("email", ""),
    }


def require_roles(*roles: str):
    async def _check(user: dict = Depends(get_current_user)) -> dict:
        try:
            require_role(user["role"], set(roles))
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "forbidden", "message": str(exc)},
            ) from exc
        return user

    return _check
