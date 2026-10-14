"""Worker entrypoint: one ARQ worker per queue, all in one process by default.

python -m leadforge_worker.main                      # every queue
python -m leadforge_worker.main --queues audit,deploy  # a subset (scale queues separately)
"""

import argparse
import asyncio
import uuid
from typing import Any

from arq import Worker
from arq.connections import RedisSettings

from leadforge.core.config import get_settings
from leadforge.core.logging import configure_logging
from leadforge.db.session import get_sessionmaker
from leadforge.models.enums import JobQueue
from leadforge.services.jobs import queue_name
from leadforge_worker.runner import execute


async def run_job(ctx: dict[str, Any], job_id: str) -> str:
    return await execute(get_sessionmaker(), uuid.UUID(job_id))


def build_worker(queue: JobQueue) -> Worker:
    return Worker(
        functions=[run_job],
        queue_name=queue_name(queue),
        redis_settings=RedisSettings.from_dsn(get_settings().redis_url),
        max_tries=20,  # retry budget is enforced per Job row; this is only a ceiling
        max_jobs=10,
        job_timeout=600,
        handle_signals=False,
    )


async def run(queues: list[JobQueue]) -> None:
    workers = [build_worker(q) for q in queues]
    try:
        await asyncio.gather(*(w.async_run() for w in workers))
    finally:
        await asyncio.gather(*(w.close() for w in workers))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queues", default=",".join(q.value for q in JobQueue))
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    asyncio.run(run([JobQueue(q.strip()) for q in args.queues.split(",") if q.strip()]))


if __name__ == "__main__":
    main()
