"""Job handler registry. Handlers are keyed by Job.kind and receive a JobContext."""

from collections.abc import Awaitable, Callable
from typing import Any

from leadforge.pipeline.context import JobContext

Handler = Callable[[JobContext], Awaitable[dict[str, Any]]]

HANDLERS: dict[str, Handler] = {}


def handler(kind: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn

    return register


class PermanentError(Exception):
    """Raise from a handler to dead-letter immediately instead of retrying."""


def load_all() -> None:
    """Import every handler module so it registers itself."""
    from leadforge.pipeline import (  # noqa: F401
        audit,
        builtin,
        discover,
        enrich,
        generate,
        maintenance,
        outreach,
    )
