"""Runs one Job row: status transitions, retries with backoff, and dead-lettering."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from arq import Retry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from leadforge.models import Job
from leadforge.models.enums import JobStatus
from leadforge_worker.handlers import HANDLERS

log = logging.getLogger("leadforge.worker")

BACKOFF_BASE_S = 10


def backoff_seconds(attempt: int) -> int:
    return int(BACKOFF_BASE_S * 2 ** (attempt - 1))


async def execute(sessionmaker: async_sessionmaker[AsyncSession], job_id: uuid.UUID) -> str:
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
                raise LookupError(f"no handler registered for kind={job.kind!r}")
            result: dict[str, Any] = await fn(db, job)
        except Exception as exc:
            await db.rollback()
            job.error = f"{type(exc).__name__}: {exc}"
            job.finished_at = datetime.now(UTC)
            retryable = job.attempts < job.max_attempts and not isinstance(exc, LookupError)
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
