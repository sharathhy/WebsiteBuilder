from typing import Any

import pytest
from arq import Retry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from leadforge.models import Job
from leadforge.models.enums import JobQueue, JobStatus
from leadforge.pipeline.context import JobContext
from leadforge.pipeline.registry import HANDLERS, PermanentError
from leadforge.pipeline.runner import InlineDispatcher, backoff_seconds, execute
from leadforge.services.container import Services
from leadforge.services.jobs import create_job


async def _job(db: AsyncSession, kind: str, max_attempts: int = 3) -> Job:
    job, _ = await create_job(
        db,
        queue=JobQueue.DISCOVER,
        kind=kind,
        idempotency_key=f"t:{kind}",
        max_attempts=max_attempts,
    )
    return job


async def _reload(sm: async_sessionmaker[AsyncSession], job: Job) -> Job:
    async with sm() as s:
        fresh = await s.get(Job, job.id)
        assert fresh is not None
        return fresh


async def test_ping_succeeds(
    sessionmaker: async_sessionmaker[AsyncSession],
    db: AsyncSession,
    services: Services,
    inline: InlineDispatcher,
) -> None:
    job = await _job(db, "ping")
    assert await execute(sessionmaker, job.id, services, inline) == "succeeded"
    fresh = await _reload(sessionmaker, job)
    assert fresh.result == {"pong": True, "job_id": str(job.id)}
    assert fresh.attempts == 1
    # Redelivery of a finished job is a no-op.
    assert await execute(sessionmaker, job.id, services, inline) == "succeeded"
    assert (await _reload(sessionmaker, job)).attempts == 1


async def test_failures_retry_then_dead_letter(
    sessionmaker: async_sessionmaker[AsyncSession],
    db: AsyncSession,
    services: Services,
    inline: InlineDispatcher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def boom(_ctx: JobContext) -> dict[str, Any]:
        raise RuntimeError("upstream 500")

    monkeypatch.setitem(HANDLERS, "boom", boom)
    job = await _job(db, "boom", max_attempts=2)
    with pytest.raises(Retry):
        await execute(sessionmaker, job.id, services, inline)
    assert (await _reload(sessionmaker, job)).status == JobStatus.FAILED
    assert await execute(sessionmaker, job.id, services, inline) == "dead"
    fresh = await _reload(sessionmaker, job)
    assert fresh.status == JobStatus.DEAD
    assert fresh.error == "RuntimeError: upstream 500"


async def test_unknown_kind_goes_straight_to_dead_letter(
    sessionmaker: async_sessionmaker[AsyncSession],
    db: AsyncSession,
    services: Services,
    inline: InlineDispatcher,
) -> None:
    job = await _job(db, "no-such-kind")
    assert await execute(sessionmaker, job.id, services, inline) == "dead"


async def test_permanent_error_skips_retries(
    sessionmaker: async_sessionmaker[AsyncSession],
    db: AsyncSession,
    services: Services,
    inline: InlineDispatcher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def bad_input(_ctx: JobContext) -> dict[str, Any]:
        raise PermanentError("business not found")

    monkeypatch.setitem(HANDLERS, "bad", bad_input)
    job = await _job(db, "bad", max_attempts=5)
    assert await execute(sessionmaker, job.id, services, inline) == "dead"
    assert (await _reload(sessionmaker, job)).attempts == 1


def test_backoff_grows() -> None:
    assert [backoff_seconds(n) for n in (1, 2, 3)] == [10, 20, 40]
