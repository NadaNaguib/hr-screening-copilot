"""Authentication endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from copilot.infrastructure.auth.service import create_access_token, hash_password, verify_password
from copilot.infrastructure.db.models import UserORM
from copilot.presentation.dependencies import get_session, require_roles

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str


@router.post("/login")
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        select(UserORM).where(UserORM.email == request.email, UserORM.is_active)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "invalid_credentials", "message": "Invalid email or password"},
        )
    token = create_access_token(user.id, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": str(user.id),
    }


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreateRequest,
    session: AsyncSession = Depends(get_session),
    admin_user: dict = Depends(require_roles("admin")),
) -> UserORM:
    user = UserORM(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_session),
    admin_user: dict = Depends(require_roles("admin")),
) -> list[UserORM]:
    result = await session.execute(select(UserORM))
    return list(result.scalars().all())


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin_user: dict = Depends(require_roles("admin")),
) -> dict:
    user = await session.get(UserORM, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if str(user.id) == str(admin_user.get("id")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete currently logged in account",
        )
    await session.delete(user)
    await session.commit()
    return {"status": "deleted", "id": str(user_id)}
