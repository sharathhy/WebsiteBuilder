"""Shared pytest fixtures. Tests never touch live APIs.

By default tests use a throwaway SQLite file. Set TEST_DATABASE_URL to a Postgres URL
(as CI does) to run the same suite against Postgres.
"""

import os
import shutil
from collections.abc import AsyncIterator, Iterator
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
from leadforge.core.dispatch import get_dispatcher, get_optional_dispatcher
from leadforge.core.security import hash_password
from leadforge.db.base import Base
from leadforge.db.session import get_db
from leadforge.main import create_app
from leadforge.models import User
from leadforge.models.enums import Role
from leadforge.pipeline.registry import load_all
from leadforge.pipeline.runner import InlineDispatcher
from leadforge.services.container import Services, build_services, set_services

load_all()

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
def services(
    tmp_path: Path, config_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Services]:
    """Mock-mode service container writing into a per-test storage dir.

    Browser audits are off and sites use the static builder so the suite stays fast;
    tests that need either turn them back on.
    """
    settings = get_settings()
    for key, value in {
        "storage_dir": tmp_path / "storage",
        "public_base_url": "http://test",
        "browser_audits": False,
        "site_builder": "static",
        "mock_apis": True,
    }.items():
        monkeypatch.setattr(settings, key, value)
    svc = build_services(settings)
    set_services(svc)
    yield svc
    set_services(None)


@pytest.fixture
def inline(sessionmaker: async_sessionmaker[AsyncSession], services: Services) -> InlineDispatcher:
    return InlineDispatcher(sessionmaker, services)


@pytest.fixture
async def client(
    sessionmaker: async_sessionmaker[AsyncSession], config_dir: Path, inline: InlineDispatcher
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_dispatcher] = lambda: inline
    app.dependency_overrides[get_optional_dispatcher] = lambda: inline

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
