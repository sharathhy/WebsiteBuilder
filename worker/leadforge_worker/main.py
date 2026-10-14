"""Worker entrypoint: one ARQ worker per queue, all in one process by default.

python -m leadforge_worker.main                        # every queue + cron
python -m leadforge_worker.main --queues audit,deploy  # a subset (scale queues separately)
"""

import argparse
import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

import sentry_sdk
from arq import Worker, cron
from arq.connections import RedisSettings

from leadforge.core.config import get_settings
from leadforge.core.logging import configure_logging
from leadforge.db.session import get_sessionmaker
from leadforge.models.enums import JobQueue
from leadforge.pipeline.registry import load_all
from leadforge.pipeline.runner import RedisDispatcher, execute
from leadforge.services.container import get_services
from leadforge.services.jobs import create_job, queue_name


async def run_job(ctx: dict[str, Any], job_id: str) -> str:
    return await execute(
        get_sessionmaker(), uuid.UUID(job_id), get_services(), RedisDispatcher(ctx["redis"])
    )


async def _enqueue_cron(ctx: dict[str, Any], queue: JobQueue, kind: str, period: str) -> None:
    async with get_sessionmaker()() as db:
        job, created = await create_job(
            db, queue=queue, kind=kind, idempotency_key=f"cron:{kind}:{period}"
        )
        if created:
            await RedisDispatcher(ctx["redis"]).dispatch(job)


async def cron_send_due(ctx: dict[str, Any]) -> None:
    now = datetime.now(UTC)
    await _enqueue_cron(ctx, JobQueue.EMAIL, "send_due", now.strftime("%Y%m%d%H%M"))


async def cron_maintenance(ctx: dict[str, Any]) -> None:
    day = datetime.now(UTC).strftime("%Y%m%d")
    for kind in ("expire_previews", "reaudit_stale", "refresh_places"):
        await _enqueue_cron(ctx, JobQueue.AUDIT, kind, day)


def build_worker(queue: JobQueue, with_cron: bool) -> Worker:
    crons = (
        [
            cron(cron_send_due, minute={0, 15, 30, 45}),
            cron(cron_maintenance, hour={3}, minute={0}),
        ]
        if with_cron
        else None
    )
    return Worker(
        functions=[run_job],
        queue_name=queue_name(queue),
        redis_settings=RedisSettings.from_dsn(get_settings().redis_url),
        max_tries=20,  # retry budget is enforced per Job row; this is only a ceiling
        max_jobs=10,
        job_timeout=1800,
        handle_signals=False,
        cron_jobs=crons,
    )


async def run(queues: list[JobQueue]) -> None:
    workers = [build_worker(q, with_cron=(i == 0)) for i, q in enumerate(queues)]
    try:
        await asyncio.gather(*(w.async_run() for w in workers))
    finally:
        await asyncio.gather(*(w.close() for w in workers))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queues", default=",".join(q.value for q in JobQueue))
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn.get_secret_value(), environment=settings.env)
    load_all()
    asyncio.run(run([JobQueue(q.strip()) for q in args.queues.split(",") if q.strip()]))


if __name__ == "__main__":
    main()
