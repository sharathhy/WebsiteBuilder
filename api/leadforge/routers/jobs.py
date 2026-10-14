import uuid

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from leadforge.core.deps import AdminUser, CurrentUser, DbSession
from leadforge.models import Job
from leadforge.models.enums import JobQueue, JobStatus
from leadforge.schemas.jobs import JobOut
from leadforge.services.jobs import create_job, dispatch

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
async def ping(request: Request, _: AdminUser, db: DbSession) -> Job:
    """Enqueue a no-op job end to end, to prove API -> Redis -> worker -> Postgres works."""
    job, _created = await create_job(
        db, queue=JobQueue.DISCOVER, kind="ping", idempotency_key=f"ping:{uuid.uuid4()}"
    )
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Queue unavailable")
    await dispatch(redis, job)
    return job
