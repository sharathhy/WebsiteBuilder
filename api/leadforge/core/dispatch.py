"""FastAPI dependency that hands routers a job dispatcher (Redis/ARQ in normal runs)."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from leadforge.pipeline.context import Dispatcher
from leadforge.pipeline.runner import RedisDispatcher


def get_dispatcher(request: Request) -> Dispatcher:
    local: Dispatcher | None = getattr(request.app.state, "local_dispatcher", None)
    if local is not None:
        return local
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Job queue unavailable")
    return RedisDispatcher(redis)


JobDispatcher = Annotated[Dispatcher, Depends(get_dispatcher)]


def get_optional_dispatcher(request: Request) -> Dispatcher | None:
    """For endpoints that still succeed when the queue is down (a cron catches up later)."""
    local: Dispatcher | None = getattr(request.app.state, "local_dispatcher", None)
    if local is not None:
        return local
    redis = getattr(request.app.state, "redis", None)
    return RedisDispatcher(redis) if redis is not None else None


OptionalDispatcher = Annotated[Dispatcher | None, Depends(get_optional_dispatcher)]
