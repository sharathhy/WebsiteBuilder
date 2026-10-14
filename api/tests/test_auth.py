import httpx
import pytest

from conftest import ADMIN, REVIEWER, login
from leadforge.models import User

pytestmark = pytest.mark.usefixtures("users")


async def test_login_and_me(client: httpx.AsyncClient) -> None:
    headers = await login(client, ADMIN)
    me = (await client.get("/api/auth/me", headers=headers)).json()
    assert me["email"] == ADMIN[0]
    assert me["role"] == "admin"
    assert "password_hash" not in me


async def test_login_is_case_insensitive_on_email(client: httpx.AsyncClient) -> None:
    await login(client, (ADMIN[0].upper(), ADMIN[1]))


@pytest.mark.parametrize(
    "username,password",
    [(ADMIN[0], "wrong-password-123"), ("nobody@example.com", "whatever-123456")],
)
async def test_bad_login(client: httpx.AsyncClient, username: str, password: str) -> None:
    resp = await client.post("/api/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 401


async def test_protected_route_needs_token(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/auth/me")).status_code == 401
    bad = {"Authorization": "Bearer not-a-jwt"}
    assert (await client.get("/api/auth/me", headers=bad)).status_code == 401


async def test_refresh_flow(client: httpx.AsyncClient) -> None:
    tokens = (
        await client.post("/api/auth/login", data={"username": ADMIN[0], "password": ADMIN[1]})
    ).json()
    resp = await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    # A refresh token must not work as an access token, and vice versa.
    as_access = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    assert (await client.get("/api/auth/me", headers=as_access)).status_code == 401
    resp = await client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert resp.status_code == 401


async def test_inactive_user_rejected(
    client: httpx.AsyncClient, db, users: dict[str, User]
) -> None:  # type: ignore[no-untyped-def]
    headers = await login(client, REVIEWER)
    users["reviewer"].is_active = False
    await db.commit()
    assert (await client.get("/api/auth/me", headers=headers)).status_code == 401


async def test_reviewer_cannot_manage_users(client: httpx.AsyncClient) -> None:
    headers = await login(client, REVIEWER)
    assert (await client.get("/api/users", headers=headers)).status_code == 403
    body = {"email": "x@example.com", "password": "long-enough-pass"}
    assert (await client.post("/api/users", json=body, headers=headers)).status_code == 403


async def test_admin_creates_user(client: httpx.AsyncClient) -> None:
    headers = await login(client, ADMIN)
    body = {"email": "New@Example.com", "password": "long-enough-pass", "role": "reviewer"}
    resp = await client.post("/api/users", json=body, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["email"] == "new@example.com"
    assert (await client.post("/api/users", json=body, headers=headers)).status_code == 409
    await login(client, ("new@example.com", "long-enough-pass"))


async def test_password_policy(client: httpx.AsyncClient) -> None:
    headers = await login(client, ADMIN)
    body = {"email": "short@example.com", "password": "short"}
    assert (await client.post("/api/users", json=body, headers=headers)).status_code == 422


async def test_admin_cannot_demote_self(client: httpx.AsyncClient, users: dict[str, User]) -> None:
    headers = await login(client, ADMIN)
    resp = await client.patch(
        f"/api/users/{users['admin'].id}", json={"role": "reviewer"}, headers=headers
    )
    assert resp.status_code == 400
