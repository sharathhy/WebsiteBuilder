"""LLM calls with budget checks and token-cost logging."""

import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from leadforge.clients.llm import LLMClient, LLMResult, Prompt
from leadforge.models.enums import ApiProvider
from leadforge.services.usage import ensure_budget, record_usage

T = TypeVar("T", bound=BaseModel)


async def call_structured(
    db: AsyncSession,
    llm: LLMClient,
    prompt: Prompt,
    variables: dict[str, Any],
    output: type[T],
    *,
    mock: Callable[[], T],
    images: list[bytes] | None = None,
    job_id: uuid.UUID | None = None,
    estimate_usd: float = 0.05,
) -> LLMResult[T]:
    if llm.provider != "mock":
        await ensure_budget(db, ApiProvider.ANTHROPIC, estimate_usd)
    result = await llm.structured(prompt, variables, output, mock=mock, images=images)
    await record_usage(
        db,
        ApiProvider.ANTHROPIC,
        prompt.ref,
        cost_usd=result.cost_usd,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        mocked=result.mocked,
        job_id=job_id,
        meta={"model": result.model},
    )
    return result
