"""Provider-agnostic LLM layer with structured (Pydantic) outputs.

Call sites pass a versioned Prompt, the output model, optional images, and a `mock`
callable that produces a deterministic result for MOCK_APIS mode. Token usage and cost
come back on every result so callers can log them to api_usage.
"""

import base64
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# USD per million tokens (input, output).
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    system: str
    user: str  # str.format template

    @property
    def ref(self) -> str:
        return f"{self.id}@{self.version}"

    def render(self, variables: dict[str, Any]) -> str:
        return self.user.format(**variables)

    def render_system(self, variables: dict[str, Any]) -> str:
        return self.system.format(**variables)


@dataclass
class LLMResult(Generic[T]):
    data: T
    model: str
    prompt_ref: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    mocked: bool


class LLMError(RuntimeError):
    pass


def cost_for(model: str, tokens_in: int, tokens_out: int) -> float:
    pin, pout = PRICING.get(model, PRICING["claude-opus-5-5"])
    return tokens_in / 1_000_000 * pin + tokens_out / 1_000_000 * pout


class LLMClient(Protocol):
    provider: str

    async def structured(
        self,
        prompt: Prompt,
        variables: dict[str, Any],
        output: type[T],
        *,
        mock: Callable[[], T],
        images: list[bytes] | None = None,
        max_tokens: int = 8000,
    ) -> LLMResult[T]: ...


class AnthropicLLM:
    provider = "anthropic"

    def __init__(self, api_key: str, model: str, effort: str = "medium") -> None:
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.effort = effort

    async def structured(
        self,
        prompt: Prompt,
        variables: dict[str, Any],
        output: type[T],
        *,
        mock: Callable[[], T],
        images: list[bytes] | None = None,
        max_tokens: int = 8000,
    ) -> LLMResult[T]:
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.standard_b64encode(img).decode(),
                },
            }
            for img in images or []
        ]
        content.append({"type": "text", "text": prompt.render(variables)})
        response = await self.client.beta.messages.parse(
            model=self.model,
            max_tokens=max_tokens,
            system=prompt.render_system(variables),
            messages=[{"role": "user", "content": content}],  # type: ignore[typeddict-item]
            output_format=output,
            output_config={"effort": self.effort},  # type: ignore[arg-type]
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise LLMError(f"model declined prompt {prompt.ref}")
        parsed = response.parsed_output
        if parsed is None:
            raise LLMError(f"no structured output for {prompt.ref} ({response.stop_reason})")
        tin, tout = response.usage.input_tokens, response.usage.output_tokens
        return LLMResult(
            data=parsed,
            model=response.model,
            prompt_ref=prompt.ref,
            tokens_in=tin,
            tokens_out=tout,
            cost_usd=cost_for(response.model, tin, tout),
            mocked=False,
        )


class MockLLM:
    provider = "mock"

    async def structured(
        self,
        prompt: Prompt,
        variables: dict[str, Any],
        output: type[T],
        *,
        mock: Callable[[], T],
        images: list[bytes] | None = None,
        max_tokens: int = 8000,
    ) -> LLMResult[T]:
        data = output.model_validate(mock().model_dump())
        return LLMResult(data, "mock", prompt.ref, 0, 0, 0.0, mocked=True)
