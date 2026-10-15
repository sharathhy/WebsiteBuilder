"""LeadForge API entrypoint."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from leadforge.core.config import get_settings
from leadforge.core.logging import configure_logging
from leadforge.core.middleware import RequestContextMiddleware
from leadforge.core.ratelimit import limiter
from leadforge.routers import (
    analytics,
    auth,
    campaigns,
    drafts,
    health,
    jobs,
    leads,
    metrics,
    public,
    suppression,
    targets,
    users,
    webhooks,
)

log = logging.getLogger("leadforge.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.redis = None
    app.state.local_dispatcher = None
    if settings.job_runner == "inline" and settings.env != "test":
        from leadforge.db.session import get_sessionmaker
        from leadforge.pipeline.registry import load_all
        from leadforge.pipeline.runner import BackgroundDispatcher
        from leadforge.services.container import get_services

        load_all()
        app.state.local_dispatcher = BackgroundDispatcher(get_sessionmaker(), get_services())
        log.info("local mode: jobs run inside the API process (no Redis)")
    elif settings.env != "test":
        try:
            app.state.redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        except Exception:
            log.warning("redis unavailable at startup; queue endpoints will return 503")
    yield
    if app.state.local_dispatcher is not None:
        await app.state.local_dispatcher.aclose()
    if app.state.redis is not None:
        await app.state.redis.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    settings.assert_safe_for_prod()
    configure_logging(settings.log_level)
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn.get_secret_value(), environment=settings.env)

    app = FastAPI(
        title="LeadForge API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.include_router(health.router)
    for router in (
        auth.router,
        users.router,
        targets.router,
        jobs.router,
        campaigns.router,
        leads.router,
        drafts.router,
        analytics.router,
        suppression.router,
        webhooks.router,
        metrics.router,
    ):
        app.include_router(router, prefix="/api")
    app.include_router(public.router)
    if settings.dashboard_dir is not None and (settings.dashboard_dir / "index.html").is_file():
        _serve_dashboard(app, settings.dashboard_dir.resolve())
    return app


# The dashboard is a same-origin single-page app; previews open in a same-origin iframe.
DASHBOARD_CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
    "frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


def _serve_dashboard(app: FastAPI, root: Path) -> None:
    """Serve the built dashboard; unknown paths get index.html for client-side routes."""
    headers = {"Content-Security-Policy": DASHBOARD_CSP}

    @app.get("/{path:path}", include_in_schema=False)
    async def dashboard(path: str) -> FileResponse:
        if path.startswith(("api/", "previews/", "files/")):
            raise HTTPException(status_code=404)
        file = (root / path).resolve()
        if path and file.is_relative_to(root) and file.is_file():
            return FileResponse(file, headers=headers)
        return FileResponse(root / "index.html", headers={**headers, "Cache-Control": "no-cache"})


app = create_app()
