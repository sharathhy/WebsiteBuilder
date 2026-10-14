"""Management commands.

python -m leadforge.cli seed   # idempotent: dev users + a demo campaign, no external calls
"""

import argparse
import asyncio
import os

from sqlalchemy import select

from leadforge.core.security import hash_password
from leadforge.db.session import get_sessionmaker
from leadforge.models import Campaign, User
from leadforge.models.enums import Role
from leadforge.services.targets import load_targets

DEMO_CAMPAIGN = "Demo: dentists in Bengaluru + Austin"


async def seed() -> None:
    admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@leadforge.local")
    admin_password = os.environ.get("SEED_ADMIN_PASSWORD", "admin-change-me-123")
    reviewer_email = os.environ.get("SEED_REVIEWER_EMAIL", "reviewer@leadforge.local")
    reviewer_password = os.environ.get("SEED_REVIEWER_PASSWORD", "reviewer-change-me-123")
    targets = load_targets()

    async with get_sessionmaker()() as db:
        for email, password, role, name in (
            (admin_email, admin_password, Role.ADMIN, "Admin"),
            (reviewer_email, reviewer_password, Role.REVIEWER, "Reviewer"),
        ):
            if await db.scalar(select(User).where(User.email == email)) is None:
                db.add(
                    User(
                        email=email,
                        password_hash=hash_password(password),
                        role=role,
                        full_name=name,
                    )
                )
                print(f"created {role.value}: {email}")
            else:
                print(f"exists  {role.value}: {email}")

        if await db.scalar(select(Campaign).where(Campaign.name == DEMO_CAMPAIGN)) is None:
            d = targets.defaults
            db.add(
                Campaign(
                    name=DEMO_CAMPAIGN,
                    cities=["bengaluru", "austin"],
                    categories=["dentists"],
                    radius_m=d.radius_m,
                    max_results_per_target=d.max_results_per_target,
                    rebuild_threshold=d.rebuild_threshold,
                )
            )
            print(f"created campaign: {DEMO_CAMPAIGN}")
        await db.commit()


async def demo(cities: list[str], categories: list[str], max_results: int) -> None:
    """Run the whole pipeline in-process on mocked APIs and print a summary."""
    from collections import Counter

    from sqlalchemy import func

    from leadforge.models import Business, EmailDraft, GeneratedSite
    from leadforge.pipeline.registry import load_all
    from leadforge.pipeline.runner import InlineDispatcher
    from leadforge.services.campaigns import start_campaign
    from leadforge.services.container import get_services

    load_all()
    services = get_services()
    sm = get_sessionmaker()
    dispatcher = InlineDispatcher(sm, services)
    async with sm() as db:
        campaign = Campaign(
            name=f"CLI demo: {', '.join(categories)} in {', '.join(cities)}",
            cities=cities,
            categories=categories,
            max_results_per_target=max_results,
        )
        db.add(campaign)
        await db.commit()
        await start_campaign(db, campaign, load_targets(), dispatcher)
    ran = await dispatcher.drain()
    async with sm() as db:
        biz = list(await db.scalars(select(Business).where(Business.duplicate_of_id.is_(None))))
        grades = Counter(b.latest_grade for b in biz)
        sites = Counter(s.status.value for s in await db.scalars(select(GeneratedSite)))
        drafts = await db.scalar(select(func.count()).select_from(EmailDraft))
    print(f"jobs run: {ran}")
    print(f"businesses: {len(biz)}  with email: {sum(1 for b in biz if b.primary_email)}")
    print(f"grades: {dict(grades)}")
    print(f"generated sites: {dict(sites)}")
    print(f"outreach drafts awaiting approval: {drafts}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="leadforge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    d = sub.add_parser("demo", help="run the full pipeline in-process on mocked APIs")
    d.add_argument("--cities", default="bengaluru,austin")
    d.add_argument("--categories", default="dentists")
    d.add_argument("--max-results", type=int, default=30)
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(seed())
    elif args.command == "demo":
        asyncio.run(demo(args.cities.split(","), args.categories.split(","), args.max_results))


if __name__ == "__main__":
    main()
