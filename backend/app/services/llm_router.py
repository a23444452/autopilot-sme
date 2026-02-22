"""Multi-model LLM router with fallback chain and usage logging.

Implements a fallback chain: Claude → OpenAI → Ollama.
Normalizes responses across providers into a unified format.
Logs usage (tokens, cost, latency) per call.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic
import openai

from app.core.config import settings

logger = logging.getLogger(__name__)

# Default models per provider
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"


@dataclass
class LLMResponse:
    """Normalized response from any LLM provider."""

    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class _UsageRecord:
    """Internal record of a single LLM call for logging."""

    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    task_type: str
    success: bool
    error: str | None = None


class LLMRouter:
    """Routes LLM calls through a multi-model fallback chain with usage tracking."""

    def __init__(self) -> None:
        self._anthropic: anthropic.AsyncAnthropic | None = None
        self._openai: openai.AsyncOpenAI | None = None
        self._usage_log: list[_UsageRecord] = []

        # Initialize clients based on available API keys
        if settings.ANTHROPIC_API_KEY:
            self._anthropic = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
            )

        if settings.OPENAI_API_KEY:
            self._openai = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
            )

    async def call(
        self,
        prompt: str,
        system: str = "",
        task_type: str = "general",
        prefer_local: bool = False,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Send a prompt through the fallback chain and return a normalized response.

        Fallback order: Claude → OpenAI → Ollama.
        If ``prefer_local`` is True, Ollama is tried first.
        """
        providers: list[str] = (
            ["ollama", "claude", "openai"] if prefer_local
            else ["claude", "openai", "ollama"]
        )

        last_error: Exception | None = None

        for provider in providers:
            try:
                if provider == "claude" and self._anthropic:
                    return await self._call_claude(prompt, system, task_type, max_tokens)
                elif provider == "openai" and self._openai:
                    return await self._call_openai(prompt, system, task_type, max_tokens)
                elif provider == "ollama":
                    return await self._call_ollama(prompt, system, task_type, max_tokens)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM provider %s failed for task_type=%s: %s",
                    provider, task_type, exc,
                )
                self._log_usage(
                    provider=provider,
                    model="",
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=0,
                    task_type=task_type,
                    success=False,
                    error=str(exc),
                )

        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        )

    # -------------------------------------------------------------------
    # Provider implementations
    # -------------------------------------------------------------------

    async def _call_claude(
        self, prompt: str, system: str, task_type: str, max_tokens: int,
    ) -> LLMResponse:
        """Call Anthropic Claude API."""
        assert self._anthropic is not None
        model = DEFAULT_CLAUDE_MODEL
        start = time.monotonic()

        message = await self._anthropic.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system or "You are a helpful manufacturing scheduling assistant.",
            messages=[{"role": "user", "content": prompt}],
        )

        latency = (time.monotonic() - start) * 1000
        content = message.content[0].text if message.content else ""
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        self._log_usage(
            provider="claude",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            task_type=task_type,
            success=True,
        )

        return LLMResponse(
            content=content,
            provider="claude",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency, 1),
        )

    async def _call_openai(
        self, prompt: str, system: str, task_type: str, max_tokens: int,
    ) -> LLMResponse:
        """Call OpenAI API."""
        assert self._openai is not None
        model = DEFAULT_OPENAI_MODEL
        start = time.monotonic()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._openai.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
        )

        latency = (time.monotonic() - start) * 1000
        content = response.choices[0].message.content or ""
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        self._log_usage(
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            task_type=task_type,
            success=True,
        )

        return LLMResponse(
            content=content,
            provider="openai",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency, 1),
        )

    async def _call_ollama(
        self, prompt: str, system: str, task_type: str, max_tokens: int,
    ) -> LLMResponse:
        """Call Ollama local LLM via OpenAI-compatible endpoint."""
        model = DEFAULT_OLLAMA_MODEL
        start = time.monotonic()

        client = openai.AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",  # Ollama doesn't require a real key
        )

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
        )

        latency = (time.monotonic() - start) * 1000
        content = response.choices[0].message.content or ""
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        self._log_usage(
            provider="ollama",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            task_type=task_type,
            success=True,
        )

        return LLMResponse(
            content=content,
            provider="ollama",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency, 1),
        )

    # -------------------------------------------------------------------
    # Usage logging
    # -------------------------------------------------------------------

    def _log_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        task_type: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Record usage for auditing and compliance."""
        record = _UsageRecord(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency_ms, 1),
            task_type=task_type,
            success=success,
            error=error,
        )
        self._usage_log.append(record)
        logger.info(
            "LLM usage: provider=%s model=%s tokens=%d+%d latency=%.0fms task=%s ok=%s",
            provider, model, input_tokens, output_tokens, latency_ms, task_type, success,
        )

    def get_usage_log(self) -> list[dict[str, Any]]:
        """Return usage log as a list of dicts for compliance reporting."""
        return [
            {
                "provider": r.provider,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "latency_ms": r.latency_ms,
                "task_type": r.task_type,
                "success": r.success,
                "error": r.error,
            }
            for r in self._usage_log
        ]
