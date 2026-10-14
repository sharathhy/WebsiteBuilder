import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from leadforge.core.deps import AdminUser, CurrentUser, DbSession
from leadforge.core.dispatch import JobDispatcher
from leadforge.models import Business, Campaign, Job, campaign_businesses
from leadforge.schemas.jobs import JobOut
from leadforge.schemas.leads import CampaignIn, CampaignOut, CampaignProgress
from leadforge.services.campaigns import start_campaign
from leadforge.services.targets import load_targets

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(_: CurrentUser, db: DbSession) -> list[Campaign]:
    return list(await db.scalars(select(Campaign).order_by(Campaign.created_at.desc())))


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(body: CampaignIn, user: AdminUser, db: DbSession) -> Campaign:
    targets = load_targets()
    unknown = (set(body.cities) - {c.id for c in targets.cities}) | (
        set(body.categories) - {c.id for c in targets.categories}
    )
    if unknown:
        raise HTTPException(422, f"Unknown city or category ids: {', '.join(sorted(unknown))}")
    campaign = Campaign(**body.model_dump(), created_by_id=user.id)
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def _get(db: DbSession, campaign_id: uuid.UUID) -> Campaign:
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    return campaign


@router.post("/{campaign_id}/run", response_model=list[JobOut], status_code=202)
async def run_campaign(
    campaign_id: uuid.UUID, _: AdminUser, db: DbSession, dispatcher: JobDispatcher
) -> list[Job]:
    """Queue discovery for every (city x category). Uses Places quota; mock in dev."""
    campaign = await _get(db, campaign_id)
    return await start_campaign(db, campaign, load_targets(), dispatcher)


@router.get("/{campaign_id}/progress", response_model=CampaignProgress)
async def progress(campaign_id: uuid.UUID, _: CurrentUser, db: DbSession) -> CampaignProgress:
    campaign = await _get(db, campaign_id)
    ids = select(campaign_businesses.c.business_id).where(
        campaign_businesses.c.campaign_id == campaign_id
    )
    job_rows = await db.execute(
        select(Job.queue, Job.status, func.count())
        .where((Job.campaign_id == campaign_id) | Job.business_id.in_(ids))
        .group_by(Job.queue, Job.status)
    )
    jobs: dict[str, dict[str, int]] = {}
    for queue, st, n in job_rows:
        jobs.setdefault(queue.value, {})[st.value] = n
    lead_rows = await db.execute(
        select(Business.lead_status, func.count())
        .where(Business.id.in_(ids), Business.duplicate_of_id.is_(None))
        .group_by(Business.lead_status)
    )
    leads = {st.value: n for st, n in lead_rows}
    return CampaignProgress(
        campaign=CampaignOut.model_validate(campaign),
        jobs=jobs,
        leads=leads,
        total_leads=sum(leads.values()),
    )
