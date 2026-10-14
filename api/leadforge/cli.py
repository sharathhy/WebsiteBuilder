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


def main() -> None:
    parser = argparse.ArgumentParser(prog="leadforge")
    parser.add_argument("command", choices=["seed"])
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(seed())


if __name__ == "__main__":
    main()
