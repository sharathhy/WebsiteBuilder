import httpx


async def test_liveness(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.json() == {"status": "ok"}


async def test_readiness_reports_db(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["checks"]["database"] == "ok"


async def test_request_id_and_security_headers(client) -> None:  # type: ignore[no-untyped-def]
    resp = await client.get("/health", headers={"X-Request-ID": "abc123"})
    assert resp.headers["x-request-id"] == "abc123"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]


async def test_metrics_requires_admin(client, users) -> None:  # type: ignore[no-untyped-def]
    from conftest import ADMIN, REVIEWER, login

    assert (await client.get("/api/metrics")).status_code == 401
    assert (
        await client.get("/api/metrics", headers=await login(client, REVIEWER))
    ).status_code == 403
    resp = await client.get("/api/metrics", headers=await login(client, ADMIN))
    assert resp.status_code == 200 and "leadforge_spend_usd_month 0.0000" in resp.text


async def test_ping_runs_through_the_dispatcher(client, users) -> None:  # type: ignore[no-untyped-def]
    """The queue check works without Redis too (local mode uses the in-process runner)."""
    from conftest import ADMIN, login

    headers = await login(client, ADMIN)
    resp = await client.post("/api/jobs/ping", headers=headers)
    assert resp.status_code == 202, resp.text
    jobs = (await client.get("/api/jobs", headers=headers)).json()
    assert jobs[0]["kind"] == "ping"
