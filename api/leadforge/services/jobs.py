"""Idempotent job creation. Workers pick jobs up from Redis; Postgres holds the durable record."""

import uuid
from typing import Any

from arq.connections import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import Job
from leadforge.models.enums import JobQueue

QUEUE_PREFIX = "leadforge:queue:"


def queue_name(queue: JobQueue) -> str:
    return f"{QUEUE_PREFIX}{queue.value}"


async def create_job(
    db: AsyncSession,
    *,
    queue: JobQueue,
    kind: str,
    idempotency_key: str,
    payload: dict[str, Any] | None = None,
    max_attempts: int = 3,
    campaign_id: uuid.UUID | None = None,
    business_id: uuid.UUID | None = None,
) -> tuple[Job, bool]:
    """Return (job, created). An existing key returns the existing job untouched."""
    existing = await db.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
    if existing is not None:
        return existing, False
    job = Job(
        queue=queue,
        kind=kind,
        idempotency_key=idempotency_key,
        payload=payload or {},
        max_attempts=max_attempts,
        campaign_id=campaign_id,
        business_id=business_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job, True


async def dispatch(redis: ArqRedis, job: Job) -> None:
    """Push the job onto its ARQ queue. ARQ's _job_id dedups on the Redis side too."""
    await redis.enqueue_job(
        "run_job", str(job.id), _job_id=str(job.id), _queue_name=queue_name(job.queue)
    )
