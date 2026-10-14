import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.test_pipeline import run_campaign

from leadforge.models import Audit, Business
from leadforge.models.enums import AuditStatus, JobQueue
from leadforge.pipeline.runner import InlineDispatcher
from leadforge.scoring import rubric
from leadforge.services.jobs import create_job


@pytest.mark.parametrize(
    ("score", "grade"),
    [(100, "A"), (85, "A"), (84, "B"), (70, "B"), (69, "C"), (50, "C"), (49, "D")],
)
def test_grade_boundaries(score: int, grade: str) -> None:
    assert rubric.grade_for(score) == grade


def test_category_weights_sum_to_100() -> None:
    assert sum(rubric.CATEGORY_MAX.values()) == 100


def test_no_website_scores_zero_with_reason() -> None:
    result = rubric.no_website_result("Dentists", "Austin")
    assert result.total == 0 and result.grade == "D"
    assert result.top_issues


async def test_rescoring_the_same_site_is_stable(
    db: AsyncSession, inline: InlineDispatcher
) -> None:
    """Acceptance: the same site scores within +/-3 points across runs."""
    await run_campaign(db, inline, ["austin"], 8)
    sites = list(
        await db.scalars(
            select(Business).where(
                Business.has_website.is_(True), Business.latest_score.is_not(None)
            )
        )
    )
    assert sites
    before = {b.id: b.latest_score for b in sites}
    for b in sites:
        job, _ = await create_job(
            db, queue=JobQueue.AUDIT, kind="audit", business_id=b.id,
            idempotency_key=f"audit:{b.id}:again", payload={"force": True},
        )  # fmt: skip
        await inline.dispatch(job)
    await inline.drain()
    for b in sites:
        await db.refresh(b)
        assert abs((b.latest_score or 0) - (before[b.id] or 0)) <= 3, b.name
        audits = list(
            await db.scalars(
                select(Audit).where(
                    Audit.business_id == b.id,
                    Audit.generated_site_id.is_(None),
                    Audit.status == AuditStatus.COMPLETED,
                )
            )
        )
        assert len(audits) == 2
        # Each score is explained: per-category breakdown that adds up to the total.
        for a in audits:
            total = sum(v["score"] for v in a.breakdown.values())
            assert abs(total - (a.total_score or 0)) <= 1
            assert set(a.breakdown) == set(rubric.CATEGORY_MAX)
