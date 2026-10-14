"""Runs one Job row: status transitions, retries with backoff, and dead-lettering."""

import logging
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from arq import Retry
from arq.connections import ArqRedis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from leadforge.models import Job
from leadforge.models.enums import JobStatus
from leadforge.pipeline.context import Dispatcher, JobContext
from leadforge.pipeline.registry import HANDLERS, PermanentError
from leadforge.services.container import Services
from leadforge.services.jobs import dispatch as redis_dispatch

log = logging.getLogger("leadforge.worker")

BACKOFF_BASE_S = 10


def backoff_seconds(attempt: int) -> int:
    return int(BACKOFF_BASE_S * 2 ** (attempt - 1))


async def execute(
    sessionmaker: async_sessionmaker[AsyncSession],
    job_id: uuid.UUID,
    services: Services,
    dispatcher: Dispatcher,
) -> str:
    """Return the job's final status for this attempt. Raises arq.Retry to reschedule."""
    async with sessionmaker() as db:
        job = await db.get(Job, job_id)
        if job is None:
            log.error("job not found", extra={"job_id": str(job_id)})
            return "missing"
        if job.status in (JobStatus.SUCCEEDED, JobStatus.DEAD):
            # Idempotency: a redelivered message for a finished job is a no-op.
            return job.status.value

        job.status = JobStatus.RUNNING
        job.attempts += 1
        job.started_at = datetime.now(UTC)
        job.error = None
        await db.commit()

        fn = HANDLERS.get(job.kind)
        try:
            if fn is None:
                raise PermanentError(f"no handler registered for kind={job.kind!r}")
            result: dict[str, Any] = await fn(JobContext(db, job, services, dispatcher))
        except Exception as exc:
            await db.rollback()
            job = await db.get(Job, job_id)
            assert job is not None
            job.error = f"{type(exc).__name__}: {exc}"[:2000]
            job.finished_at = datetime.now(UTC)
            retryable = job.attempts < job.max_attempts and not isinstance(exc, PermanentError)
            job.status = JobStatus.FAILED if retryable else JobStatus.DEAD
            await db.commit()
            log.warning(
                "job failed",
                extra={
                    "job_id": str(job.id),
                    "kind": job.kind,
                    "attempt": job.attempts,
                    "dead": not retryable,
                    "error": job.error,
                },
            )
            if retryable:
                raise Retry(defer=backoff_seconds(job.attempts)) from exc
            return job.status.value

        job.status = JobStatus.SUCCEEDED
        job.result = result
        job.finished_at = datetime.now(UTC)
        await db.commit()
        log.info("job succeeded", extra={"job_id": str(job.id), "kind": job.kind})
        return job.status.value


class RedisDispatcher:
    def __init__(self, redis: ArqRedis) -> None:
        self.redis = redis

    async def dispatch(self, job: Job) -> None:
        await redis_dispatch(self.redis, job)


class InlineDispatcher:
    """Runs jobs in-process, breadth-first. Used by tests, `make demo` and the CLI.

    Retries happen immediately (no backoff) so a pipeline run is deterministic.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession], services: Services) -> None:
        self.sessionmaker = sessionmaker
        self.services = services
        self.pending: deque[uuid.UUID] = deque()

    async def dispatch(self, job: Job) -> None:
        self.pending.append(job.id)

    async def drain(self, limit: int = 100_000) -> int:
        ran = 0
        while self.pending and ran < limit:
            job_id = self.pending.popleft()
            ran += 1
            try:
                await execute(self.sessionmaker, job_id, self.services, self)
            except Retry:
                self.pending.append(job_id)
        return ran
