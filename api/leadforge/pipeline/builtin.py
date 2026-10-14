from typing import Any

from leadforge.pipeline.context import JobContext
from leadforge.pipeline.registry import handler


@handler("ping")
async def ping(ctx: JobContext) -> dict[str, Any]:
    return {"pong": True, "job_id": str(ctx.job.id)}
