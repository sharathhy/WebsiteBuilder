from typing import Any

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text

from leadforge.core.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request, response: Response, db: DbSession) -> dict[str, Any]:
    checks: dict[str, str] = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        checks["redis"] = "not configured"
    else:
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {type(exc).__name__}"
    healthy = checks["database"] == "ok" and checks["redis"] in ("ok", "not configured")
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if healthy else "degraded", "checks": checks}
