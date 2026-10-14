"""API usage logging, quota tracking and the monthly budget cap."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.models import ApiUsage
from leadforge.models.enums import ApiProvider
from leadforge.pipeline.registry import PermanentError
from leadforge.services.agency import load_agency

# Free-tier allowances per calendar month (units = requests unless noted).
FREE_QUOTAS: dict[ApiProvider, int] = {
    ApiProvider.PAGESPEED: 25_000 * 30,  # 25k/day
    ApiProvider.VERCEL: 100,  # deployments/day on Hobby; tracked monthly here as a soft cap
}


class BudgetExceeded(PermanentError):
    pass


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def month_spend(db: AsyncSession, provider: ApiProvider | None = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(ApiUsage.cost_usd), 0)).where(
        ApiUsage.created_at >= month_start(), ApiUsage.mocked.is_(False)
    )
    if provider:
        stmt = stmt.where(ApiUsage.provider == provider)
    return Decimal(str(await db.scalar(stmt) or 0))


async def ensure_budget(db: AsyncSession, provider: ApiProvider, estimated_usd: float) -> None:
    """Refuse a live paid call that would push spend past the configured caps."""
    agency = load_agency()
    total = await month_spend(db)
    if float(total) + estimated_usd > agency.monthly_budget_usd:
        raise BudgetExceeded(
            f"monthly budget ${agency.monthly_budget_usd:.2f} reached (spent ${total:.2f})"
        )
    cap = agency.provider_budgets_usd.get(provider.value)
    if cap is not None:
        spent = await month_spend(db, provider)
        if float(spent) + estimated_usd > cap:
            raise BudgetExceeded(f"{provider.value} budget ${cap:.2f} reached")


async def record_usage(
    db: AsyncSession,
    provider: ApiProvider,
    operation: str,
    *,
    cost_usd: float = 0.0,
    units: int = 1,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    mocked: bool,
    job_id: uuid.UUID | None = None,
    meta: dict[str, object] | None = None,
) -> None:
    db.add(
        ApiUsage(
            provider=provider,
            operation=operation,
            cost_usd=Decimal(str(round(cost_usd, 6))),
            units=units,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            mocked=mocked,
            job_id=job_id,
            meta=meta or {},
        )
    )
