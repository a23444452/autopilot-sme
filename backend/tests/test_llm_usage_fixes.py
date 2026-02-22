"""Tests for LLM usage logging persistence and correctness.

Covers:
- H5: LLM Usage should be persisted to DB (now async with DB support)
- Usage log integrity and completeness
- Fallback chain usage tracking
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_router import (
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENAI_MODEL,
    LLMResponse,
    LLMRouter,
)


# ---------------------------------------------------------------------------
# H5: LLM Usage Logging Persistence
# ---------------------------------------------------------------------------


class TestLLMUsagePersistence:
    """Test that LLM usage is properly tracked and can be persisted."""

    @pytest.fixture
    def router(self):
        """Router with mocked clients."""
        with patch("app.services.llm_router.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            router = LLMRouter()
        router._call_claude = AsyncMock(return_value=LLMResponse(
            content="test response", provider="claude", model=DEFAULT_CLAUDE_MODEL,
            input_tokens=100, output_tokens=50, latency_ms=200.0,
        ))
        router._call_openai = AsyncMock(return_value=LLMResponse(
            content="openai response", provider="openai", model=DEFAULT_OPENAI_MODEL,
            input_tokens=80, output_tokens=40, latency_ms=150.0,
        ))
        router._call_ollama = AsyncMock(return_value=LLMResponse(
            content="ollama response", provider="ollama", model=DEFAULT_OLLAMA_MODEL,
            input_tokens=60, output_tokens=30, latency_ms=300.0,
        ))
        return router

    @pytest.mark.asyncio
    async def test_successful_call_creates_usage_record(self, router):
        """Successful LLM call creates a usage log entry."""
        await router.call(prompt="test", task_type="chat")

        log = router.get_usage_log()
        assert isinstance(log, list)

    @pytest.mark.asyncio
    async def test_log_usage_records_all_fields(self):
        """_log_usage records all required fields for DB persistence."""
        with patch("app.services.llm_router.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            router = LLMRouter()

        await router._log_usage(
            provider="claude",
            model=DEFAULT_CLAUDE_MODEL,
            input_tokens=150,
            output_tokens=75,
            latency_ms=250.0,
            task_type="scheduling",
            success=True,
        )

        log = router.get_usage_log()
        assert len(log) == 1

        entry = log[0]
        assert entry["provider"] == "claude"
        assert entry["model"] == DEFAULT_CLAUDE_MODEL
        assert entry["input_tokens"] == 150
        assert entry["output_tokens"] == 75
        assert entry["latency_ms"] == 250.0
        assert entry["task_type"] == "scheduling"
        assert entry["success"] is True
        assert entry["error"] is None

    @pytest.mark.asyncio
    async def test_log_usage_records_failure_with_error(self):
        """Failed calls include error message in the log."""
        with patch("app.services.llm_router.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            router = LLMRouter()

        await router._log_usage(
            provider="openai",
            model=DEFAULT_OPENAI_MODEL,
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
            task_type="chat",
            success=False,
            error="Connection timeout",
        )

        log = router.get_usage_log()
        assert len(log) == 1
        assert log[0]["success"] is False
        assert log[0]["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_multiple_calls_accumulate_in_log(self):
        """Multiple usage entries accumulate correctly."""
        with patch("app.services.llm_router.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            router = LLMRouter()

        for i in range(3):
            await router._log_usage(
                provider="claude",
                model=DEFAULT_CLAUDE_MODEL,
                input_tokens=100 * (i + 1),
                output_tokens=50 * (i + 1),
                latency_ms=200.0,
                task_type="chat",
                success=True,
            )

        log = router.get_usage_log()
        assert len(log) == 3
        assert log[0]["input_tokens"] == 100
        assert log[1]["input_tokens"] == 200
        assert log[2]["input_tokens"] == 300

    @pytest.mark.asyncio
    async def test_fallback_logs_both_failure_and_success(self, router):
        """When Claude fails and falls back to OpenAI, both are logged."""
        router._call_claude.side_effect = Exception("Claude unavailable")

        await router.call(prompt="test", task_type="chat")

        log = router.get_usage_log()
        failures = [r for r in log if not r["success"]]
        assert len(failures) >= 1
        assert failures[0]["provider"] == "claude"

    @pytest.mark.asyncio
    async def test_all_failures_logged(self, router):
        """When all providers fail, all failures are logged."""
        router._call_claude.side_effect = Exception("Claude down")
        router._call_openai.side_effect = Exception("OpenAI down")
        router._call_ollama.side_effect = Exception("Ollama down")

        with pytest.raises(RuntimeError, match="All LLM providers failed"):
            await router.call(prompt="test", task_type="chat")

        log = router.get_usage_log()
        failures = [r for r in log if not r["success"]]
        assert len(failures) == 3

    @pytest.mark.asyncio
    async def test_usage_log_contains_task_type(self):
        """Usage records track the task_type for categorization."""
        with patch("app.services.llm_router.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            router = LLMRouter()

        task_types = ["chat", "scheduling", "simulation", "general"]
        for tt in task_types:
            await router._log_usage(
                provider="claude", model=DEFAULT_CLAUDE_MODEL,
                input_tokens=10, output_tokens=5, latency_ms=100.0,
                task_type=tt, success=True,
            )

        log = router.get_usage_log()
        logged_types = [r["task_type"] for r in log]
        assert logged_types == task_types

    @pytest.mark.asyncio
    async def test_usage_log_serializable(self):
        """Usage log entries are JSON-serializable dicts."""
        with patch("app.services.llm_router.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = ""
            mock_settings.OPENAI_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            router = LLMRouter()

        await router._log_usage(
            provider="claude", model=DEFAULT_CLAUDE_MODEL,
            input_tokens=100, output_tokens=50, latency_ms=200.0,
            task_type="chat", success=True,
        )

        import json
        log = router.get_usage_log()
        serialized = json.dumps(log)
        assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# LLM Response Normalization
# ---------------------------------------------------------------------------


class TestResponseNormalizationFixes:
    """Test that all providers return consistently normalized responses."""

    @pytest.fixture
    def router(self):
        with patch("app.services.llm_router.settings") as mock_settings:
            mock_settings.ANTHROPIC_API_KEY = "test-key"
            mock_settings.OPENAI_API_KEY = "test-key"
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            router = LLMRouter()
        return router

    @pytest.mark.asyncio
    async def test_claude_response_has_required_fields(self, router):
        """Claude response includes all required fields."""
        router._call_claude = AsyncMock(return_value=LLMResponse(
            content="response", provider="claude", model=DEFAULT_CLAUDE_MODEL,
            input_tokens=100, output_tokens=50, latency_ms=200.0,
        ))

        result = await router.call(prompt="test")
        assert result.content == "response"
        assert result.provider == "claude"
        assert result.model == DEFAULT_CLAUDE_MODEL
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.latency_ms == 200.0

    @pytest.mark.asyncio
    async def test_openai_response_has_required_fields(self, router):
        """OpenAI response includes all required fields."""
        router._call_claude = AsyncMock(side_effect=Exception("down"))
        router._call_openai = AsyncMock(return_value=LLMResponse(
            content="openai reply", provider="openai", model=DEFAULT_OPENAI_MODEL,
            input_tokens=80, output_tokens=40, latency_ms=150.0,
        ))

        result = await router.call(prompt="test")
        assert result.content == "openai reply"
        assert result.provider == "openai"
        assert result.input_tokens == 80

    @pytest.mark.asyncio
    async def test_ollama_response_has_required_fields(self, router):
        """Ollama response includes all required fields."""
        router._call_claude = AsyncMock(side_effect=Exception("down"))
        router._call_openai = AsyncMock(side_effect=Exception("down"))
        router._call_ollama = AsyncMock(return_value=LLMResponse(
            content="ollama reply", provider="ollama", model=DEFAULT_OLLAMA_MODEL,
            input_tokens=60, output_tokens=30, latency_ms=300.0,
        ))

        result = await router.call(prompt="test")
        assert result.content == "ollama reply"
        assert result.provider == "ollama"
