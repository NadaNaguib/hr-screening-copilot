"""Admin user management endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from copilot.infrastructure.auth.service import hash_password
from copilot.infrastructure.db.models import UserORM
from copilot.presentation.dependencies import get_session, require_roles

router = APIRouter()


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str


@router.post("/admin/users")
async def admin_create_user(
    request: CreateUserRequest,
    session: AsyncSession = Depends(get_session),
    admin_user: dict = Depends(require_roles("admin")),
) -> dict:
    user = UserORM(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {"id": str(user.id), "email": user.email, "role": user.role}


@router.delete("/admin/users/{user_id}")
async def admin_deactivate_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin_user: dict = Depends(require_roles("admin")),
) -> dict:
    user = await session.get(UserORM, user_id)
    if user:
        user.is_active = False
        await session.commit()
    return {"id": str(user_id), "is_active": False}
