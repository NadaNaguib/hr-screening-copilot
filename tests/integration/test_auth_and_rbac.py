"""Integration tests for auth and RBAC enforcement."""
from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport

from copilot.infrastructure.auth.service import create_access_token, hash_password
from copilot.infrastructure.db.models import UserORM
from copilot.presentation.main import app


@pytest.fixture
async def admin_user(session):
    user = UserORM(
        id=uuid4(),
        email="admin-test@example.com",
        hashed_password=hash_password("password123"),
        full_name="Admin Test",
        role="admin",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def recruiter_user(session):
    user = UserORM(
        id=uuid4(),
        email="recruiter-test@example.com",
        hashed_password=hash_password("password123"),
        full_name="Recruiter Test",
        role="hr_recruiter",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def manager_user(session):
    user = UserORM(
        id=uuid4(),
        email="manager-test@example.com",
        hashed_password=hash_password("password123"),
        full_name="Manager Test",
        role="hiring_manager",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_login_with_valid_credentials(admin_user):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={
            "email": "admin-test@example.com",
            "password": "password123",
        })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "admin"


async def test_login_with_invalid_credentials(admin_user):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={
            "email": "admin-test@example.com",
            "password": "wrongpassword",
        })
    assert response.status_code == 401


async def test_admin_can_create_user(admin_user):
    token = create_access_token(admin_user.id, admin_user.role)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/users",
            json={
                "email": "new-user@example.com",
                "password": "password123",
                "full_name": "New User",
                "role": "hr_recruiter",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200


async def test_recruiter_cannot_create_user(recruiter_user):
    token = create_access_token(recruiter_user.id, recruiter_user.role)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/users",
            json={
                "email": "another-user@example.com",
                "password": "password123",
                "full_name": "Another User",
                "role": "hiring_manager",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403


async def test_admin_can_access_observability(admin_user):
    token = create_access_token(admin_user.id, admin_user.role)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/settings",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200


async def test_recruiter_cannot_access_observability(recruiter_user):
    token = create_access_token(recruiter_user.id, recruiter_user.role)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/settings",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403


async def test_manager_cannot_access_observability(manager_user):
    token = create_access_token(manager_user.id, manager_user.role)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/observability/settings",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
