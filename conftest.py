"""Shared pytest fixtures. Tests never touch live APIs.

By default tests use a throwaway SQLite file. Set TEST_DATABASE_URL to a Postgres URL
(as CI does) to run the same suite against Postgres.
"""

import os
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

os.environ["ENV"] = "test"
os.environ["MOCK_APIS"] = "true"
os.environ["LOGIN_RATE_LIMIT"] = "1000/minute"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import leadforge.models  # noqa: F401
from leadforge.core.config import REPO_ROOT, get_settings
from leadforge.core.security import hash_password
from leadforge.db.base import Base
from leadforge.db.session import get_db
from leadforge.main import create_app
from leadforge.models import User
from leadforge.models.enums import Role

ADMIN = ("admin@example.com", "admin-password-123")
REVIEWER = ("reviewer@example.com", "reviewer-password-123")


@pytest.fixture
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    target = tmp_path / "config"
    shutil.copytree(REPO_ROOT / "config", target)
    monkeypatch.setattr(get_settings(), "config_dir", target)
    return target


@pytest.fixture
async def sessionmaker(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        yield session


@pytest.fixture
async def users(db: AsyncSession) -> dict[str, User]:
    out = {}
    for key, (email, password), role in (
        ("admin", ADMIN, Role.ADMIN),
        ("reviewer", REVIEWER, Role.REVIEWER),
    ):
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        out[key] = user
    await db.commit()
    return out


@pytest.fixture
async def client(
    sessionmaker: async_sessionmaker[AsyncSession], config_dir: Path
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def _get_db() -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def login(client: httpx.AsyncClient, creds: tuple[str, str]) -> dict[str, str]:
    resp = await client.post("/api/auth/login", data={"username": creds[0], "password": creds[1]})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
