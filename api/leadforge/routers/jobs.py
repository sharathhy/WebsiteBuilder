import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from leadforge.core.deps import AdminUser, CurrentUser, DbSession
from leadforge.core.dispatch import JobDispatcher
from leadforge.models import Job
from leadforge.models.enums import JobQueue, JobStatus
from leadforge.schemas.jobs import JobOut
from leadforge.services.jobs import create_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobOut])
async def list_jobs(
    _: CurrentUser,
    db: DbSession,
    queue: JobQueue | None = None,
    status_: JobStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if queue:
        stmt = stmt.where(Job.queue == queue)
    if status_:
        stmt = stmt.where(Job.status == status_)
    return list(await db.scalars(stmt))


@router.post("/ping", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def ping(_: AdminUser, db: DbSession, dispatcher: JobDispatcher) -> Job:
    """Enqueue a no-op job end to end, to prove the queue, a worker and the database work
    (Redis and the worker normally; the in-process runner in local mode)."""
    job, _created = await create_job(
        db, queue=JobQueue.DISCOVER, kind="ping", idempotency_key=f"ping:{uuid.uuid4()}"
    )
    await db.commit()
    await dispatcher.dispatch(job)
    return job


@router.post("/{job_id}/retry", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def retry(job_id: uuid.UUID, _: AdminUser, db: DbSession, dispatcher: JobDispatcher) -> Job:
    """Re-run a dead-lettered job (after fixing whatever made it fail)."""
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.DEAD:
        raise HTTPException(409, "Only dead jobs can be retried")
    job.status = JobStatus.QUEUED
    job.attempts = 0
    job.error = None
    await db.commit()
    await dispatcher.dispatch(job)
    return job
