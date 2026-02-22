"""Integration tests for end-to-end workflows.

Tests the interaction between multiple services:
- Chat -> LLM -> Memory pipeline
- Schedule generation -> Persistence -> Metrics
- Privacy -> Chat -> Local LLM routing
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.schedule import ScheduleRequest
from app.services.chat_service import ChatService
from app.services.llm_router import LLMResponse, LLMRouter
from app.services.memory_service import MemoryService
from app.services.privacy_guard import PrivacyGuard
from app.services.scheduler import SchedulerService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chat_mock_db():
    """Create a mock DB that works with ChatService's internal queries."""
    mock_db = AsyncMock()

    # ChatService calls db.execute() for schedule context and line status
    # The result needs .scalars().all() to work synchronously
    mock_scalars_result = MagicMock()
    mock_scalars_result.all.return_value = []

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalars_result

    mock_db.execute.return_value = mock_execute_result
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.delete = AsyncMock()

    return mock_db


# ---------------------------------------------------------------------------
# Chat -> LLM -> Memory Integration
# ---------------------------------------------------------------------------


class TestChatLLMMemoryIntegration:
    """Test the full chat pipeline: message -> LLM call -> memory storage."""

    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.call = AsyncMock(return_value=LLMResponse(
            content="排程建議回覆",
            provider="claude",
            model="claude-sonnet-4-6",
            input_tokens=150,
            output_tokens=80,
            latency_ms=300.0,
        ))
        return llm

    @pytest.fixture
    def mock_memory(self):
        mem = AsyncMock()
        mem.search_memories = AsyncMock(return_value=[])
        mem.create_decision = AsyncMock()
        return mem

    @pytest.fixture
    def chat_service(self, mock_llm, mock_memory):
        db = _make_chat_mock_db()
        return ChatService(
            db=db,
            llm_router=mock_llm,
            memory_service=mock_memory,
            privacy_guard=PrivacyGuard(),
        )

    @pytest.mark.asyncio
    async def test_chat_stores_decision_after_response(self, chat_service, mock_memory):
        """After receiving LLM response, conversation is stored as decision."""
        request = ChatRequest(message="下週的訂單排程如何？")
        response = await chat_service.handle_message(request)

        assert isinstance(response, ChatResponse)
        assert response.reply == "排程建議回覆"

        mock_memory.create_decision.assert_called_once()
        call_kwargs = mock_memory.create_decision.call_args.kwargs
        assert call_kwargs["decision_type"] == "chat"
        assert "下週的訂單排程如何" in call_kwargs["situation"]

    @pytest.mark.asyncio
    async def test_chat_includes_llm_metadata(self, chat_service):
        """Response metadata includes LLM provider info."""
        request = ChatRequest(message="test")
        response = await chat_service.handle_message(request)

        assert response.metadata["provider"] == "claude"
        assert response.metadata["input_tokens"] == 150
        assert response.metadata["output_tokens"] == 80

    @pytest.mark.asyncio
    async def test_chat_memory_failure_non_fatal(self, mock_llm, mock_memory):
        """Memory storage failure does not affect the chat response."""
        mock_memory.create_decision.side_effect = Exception("DB connection lost")

        db = _make_chat_mock_db()
        service = ChatService(
            db=db, llm_router=mock_llm,
            memory_service=mock_memory, privacy_guard=PrivacyGuard(),
        )

        request = ChatRequest(message="test")
        response = await service.handle_message(request)
        assert response.reply == "排程建議回覆"

    @pytest.mark.asyncio
    async def test_chat_llm_failure_returns_fallback(self, mock_memory):
        """LLM failure returns a fallback message."""
        mock_llm = AsyncMock()
        mock_llm.call.side_effect = RuntimeError("All providers failed")

        db = _make_chat_mock_db()
        service = ChatService(
            db=db, llm_router=mock_llm,
            memory_service=mock_memory, privacy_guard=PrivacyGuard(),
        )

        request = ChatRequest(message="test")
        response = await service.handle_message(request)

        assert "抱歉" in response.reply
        assert response.metadata.get("fallback") is True


# ---------------------------------------------------------------------------
# Privacy -> Chat -> Local LLM Integration
# ---------------------------------------------------------------------------


class TestPrivacyChatIntegration:
    """Test privacy-aware routing in the chat pipeline."""

    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.call = AsyncMock(return_value=LLMResponse(
            content="local response",
            provider="ollama",
            model="llama3.1:8b",
            input_tokens=50, output_tokens=25, latency_ms=500.0,
        ))
        return llm

    @pytest.fixture
    def mock_memory(self):
        mem = AsyncMock()
        mem.search_memories = AsyncMock(return_value=[])
        mem.create_decision = AsyncMock()
        return mem

    @pytest.mark.asyncio
    async def test_pii_triggers_local_llm(self, mock_llm, mock_memory):
        """Messages with PII (national ID) should use local LLM."""
        db = _make_chat_mock_db()
        service = ChatService(
            db=db, llm_router=mock_llm,
            memory_service=mock_memory, privacy_guard=PrivacyGuard(),
        )

        request = ChatRequest(message="客戶身分證 A123456789 的訂單狀態")
        await service.handle_message(request)

        call_kwargs = mock_llm.call.call_args.kwargs
        assert call_kwargs.get("prefer_local") is True

    @pytest.mark.asyncio
    async def test_no_pii_uses_cloud_llm(self, mock_llm, mock_memory):
        """Messages without PII should use cloud LLM."""
        db = _make_chat_mock_db()
        service = ChatService(
            db=db, llm_router=mock_llm,
            memory_service=mock_memory, privacy_guard=PrivacyGuard(),
        )

        request = ChatRequest(message="今天的排程進度如何？")
        await service.handle_message(request)

        call_kwargs = mock_llm.call.call_args.kwargs
        assert call_kwargs.get("prefer_local") is False

    @pytest.mark.asyncio
    async def test_pii_sanitized_before_llm(self, mock_llm, mock_memory):
        """PII should be masked before sending to LLM."""
        db = _make_chat_mock_db()
        service = ChatService(
            db=db, llm_router=mock_llm,
            memory_service=mock_memory, privacy_guard=PrivacyGuard(),
        )

        request = ChatRequest(message="客戶身分證 A123456789")
        await service.handle_message(request)

        call_kwargs = mock_llm.call.call_args.kwargs
        prompt = call_kwargs.get("prompt", "")
        assert "A123456789" not in prompt


# ---------------------------------------------------------------------------
# Scheduler End-to-End Tests
# ---------------------------------------------------------------------------


class TestSchedulerEndToEnd:
    """Test scheduler from request to result."""

    @pytest.mark.asyncio
    async def test_generate_schedule_with_no_orders(self, mock_db):
        """Empty database returns warning about no orders."""
        svc = SchedulerService(mock_db)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        request = ScheduleRequest()
        result = await svc.generate_schedule(request)

        assert result.total_jobs == 0
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_generate_schedule_with_no_lines(self, mock_db):
        """No production lines returns appropriate warning."""
        svc = SchedulerService(mock_db)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                order = MagicMock()
                order.items = []
                mock_result.scalars.return_value.all.return_value = [order]
            else:
                mock_result.scalars.return_value.all.return_value = []
            return mock_result

        mock_db.execute = mock_execute
        request = ScheduleRequest()
        result = await svc.generate_schedule(request)

        assert result.total_jobs == 0
        assert any("line" in w.lower() or "no" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# Memory Lifecycle Integration
# ---------------------------------------------------------------------------


class TestMemoryLifecycleIntegration:
    """Test memory creation through lifecycle transitions."""

    @pytest.fixture
    def memory_service(self, mock_db):
        mock_qdrant = AsyncMock()
        mock_embedding = AsyncMock()
        mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)
        mock_qdrant.upsert = AsyncMock()
        return MemoryService(db=mock_db, qdrant=mock_qdrant, embedding_service=mock_embedding)

    @pytest.mark.asyncio
    async def test_new_memory_starts_as_hot(self, memory_service, mock_db):
        """Newly created memories have lifecycle='hot'."""
        await memory_service.create_memory(
            memory_type="episodic",
            category="scheduling",
            content="Test scheduling memory",
        )

        assert mock_db.add.call_count >= 1
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.lifecycle == "hot"

    @pytest.mark.asyncio
    async def test_memory_importance_calculated(self, memory_service, mock_db):
        """Memory importance is auto-calculated on creation."""
        await memory_service.create_memory(
            memory_type="episodic",
            category="rush_order",
            content="緊急訂單需要立即處理",
        )

        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.importance > 0.5

    @pytest.mark.asyncio
    async def test_episodic_memory_stored_in_qdrant(self, memory_service):
        """Episodic memories are also stored in vector DB."""
        await memory_service.create_memory(
            memory_type="episodic",
            category="test",
            content="Test content for vector storage",
        )
        memory_service.qdrant.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_structured_memory_not_in_qdrant(self, memory_service):
        """Structured memories are NOT stored in vector DB."""
        await memory_service.create_memory(
            memory_type="structured",
            category="test",
            content="Structured fact",
        )
        memory_service.qdrant.upsert.assert_not_called()
