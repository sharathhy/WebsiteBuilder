"""Starting campaigns: one discover job per enabled (city x category) in the campaign."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import Campaign, Job
from leadforge.models.enums import CampaignStatus, JobQueue
from leadforge.pipeline.context import Dispatcher
from leadforge.schemas.targets import TargetsConfig
from leadforge.services.jobs import create_job


async def start_campaign(
    db: AsyncSession, campaign: Campaign, targets: TargetsConfig, dispatcher: Dispatcher
) -> list[Job]:
    city_ids = {c.id for c in targets.cities}
    cat_ids = {c.id for c in targets.categories}
    run = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    jobs: list[Job] = []
    for city in campaign.cities:
        for category in campaign.categories:
            if city not in city_ids or category not in cat_ids:
                continue
            job, created = await create_job(
                db,
                queue=JobQueue.DISCOVER,
                kind="discover",
                idempotency_key=f"discover:{campaign.id}:{city}:{category}:{run}",
                payload={"city_id": city, "category_id": category},
                campaign_id=campaign.id,
            )
            if created:
                await dispatcher.dispatch(job)
            jobs.append(job)
    campaign.status = CampaignStatus.RUNNING
    await db.commit()
    return jobs
