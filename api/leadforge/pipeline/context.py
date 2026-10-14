import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import Job
from leadforge.models.enums import JobQueue
from leadforge.services.jobs import create_job

if TYPE_CHECKING:
    from leadforge.services.container import Services


class Dispatcher(Protocol):
    async def dispatch(self, job: Job) -> None: ...


@dataclass
class JobContext:
    db: AsyncSession
    job: Job
    services: "Services"
    dispatcher: Dispatcher

    async def enqueue(
        self,
        queue: JobQueue,
        kind: str,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        *,
        business_id: uuid.UUID | None = None,
        campaign_id: uuid.UUID | None = None,
    ) -> Job:
        job, created = await create_job(
            self.db,
            queue=queue,
            kind=kind,
            idempotency_key=idempotency_key,
            payload=payload,
            business_id=business_id,
            campaign_id=campaign_id or self.job.campaign_id,
        )
        if created:
            await self.dispatcher.dispatch(job)
        return job
