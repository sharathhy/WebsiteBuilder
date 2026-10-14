import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.db.base import Base
from leadforge.models import Audit, Business, SuppressionEntry
from leadforge.models.enums import JobQueue
from leadforge.services.jobs import create_job

REQUIRED_TABLES = {
    "campaigns",
    "businesses",
    "contacts",
    "websites",
    "audits",
    "screenshots",
    "generated_sites",
    "email_drafts",
    "email_events",
    "suppression_list",
    "jobs",
    "api_usage",
    "users",
}


def test_all_required_tables_exist() -> None:
    assert set(Base.metadata.tables) >= REQUIRED_TABLES


def _business() -> Business:
    return Business(
        place_id="fixture-place-1",
        name="Fixture Dental",
        normalized_name="fixture dental",
        category="dentists",
        address="1 Fixture Rd",
        city="Bengaluru",
        country="IN",
    )


async def test_place_id_is_unique(db: AsyncSession) -> None:
    db.add(_business())
    await db.commit()
    db.add(_business())
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_audit_needs_exactly_one_target(db: AsyncSession) -> None:
    biz = _business()
    db.add(biz)
    await db.commit()
    db.add(Audit(business_id=biz.id, target_url="https://x.test", rubric_version="1.0"))
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_suppression_needs_a_key(db: AsyncSession) -> None:
    db.add(SuppressionEntry(reason="manual"))
    with pytest.raises(IntegrityError):
        await db.commit()


async def test_job_idempotency(db: AsyncSession) -> None:
    a, created_a = await create_job(db, queue=JobQueue.AUDIT, kind="audit", idempotency_key="k1")
    b, created_b = await create_job(db, queue=JobQueue.AUDIT, kind="audit", idempotency_key="k1")
    assert created_a and not created_b
    assert a.id == b.id
