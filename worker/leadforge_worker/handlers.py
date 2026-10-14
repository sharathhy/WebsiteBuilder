"""Job handlers, keyed by Job.kind. Later phases register discover/enrich/audit/... here."""

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import Job

Handler = Callable[[AsyncSession, Job], Awaitable[dict[str, Any]]]

HANDLERS: dict[str, Handler] = {}


def handler(kind: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn

    return register


@handler("ping")
async def ping(_db: AsyncSession, job: Job) -> dict[str, Any]:
    return {"pong": True, "job_id": str(job.id)}
