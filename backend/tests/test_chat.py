"""Tests for ChatService: context building, LLM response handling, memory updates."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService, SYSTEM_PROMPT, MAX_CONTEXT_TOKENS
from app.services.llm_router import LLMResponse
from app.services.privacy_guard import PrivacyGuard


# ---------------------------------------------------------------------------
# ChatService Unit Tests
# ---------------------------------------------------------------------------


class TestChatService:
    """Test ChatService.handle_message orchestration."""

    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.call = AsyncMock(return_value=LLMResponse(
            content="AI回覆測試",
            provider="claude",
            model="claude-sonnet-4-6",
            input_tokens=100,
            output_tokens=50,
            latency_ms=200.0,
        ))
        return llm

    @pytest.fixture
    def mock_memory(self):
        mem = AsyncMock()
        mem.search_memories = AsyncMock(return_value=[])
        mem.create_decision = AsyncMock()
        return mem

    @pytest.fixture
    def chat_service(self, mock_db, mock_llm, mock_memory):
        return ChatService(
            db=mock_db,
            llm_router=mock_llm,
            memory_service=mock_memory,
            privacy_guard=PrivacyGuard(),
        )

    @pytest.mark.asyncio
    async def test_handle_message_returns_chat_response(self, chat_service):
        """handle_message returns a ChatResponse with reply."""
        request = ChatRequest(message="訂單何時交貨？")
        response = await chat_service.handle_message(request)
        assert isinstance(response, ChatResponse)
        assert response.reply == "AI回覆測試"

    @pytest.mark.asyncio
    async def test_handle_message_generates_conversation_id(self, chat_service):
        """A new conversation_id is generated when not provided."""
        request = ChatRequest(message="test")
        response = await chat_service.handle_message(request)
        assert response.conversation_id is not None
        assert len(response.conversation_id) > 0

    @pytest.mark.asyncio
    async def test_handle_message_preserves_conversation_id(self, chat_service):
        """Provided conversation_id is preserved."""
        request = ChatRequest(message="test", conversation_id="conv-123")
        response = await chat_service.handle_message(request)
        assert response.conversation_id == "conv-123"

    @pytest.mark.asyncio
    async def test_handle_message_calls_llm(self, chat_service, mock_llm):
        """handle_message calls LLM router."""
        request = ChatRequest(message="test question")
        await chat_service.handle_message(request)
        mock_llm.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_stores_memory(self, chat_service, mock_memory):
        """handle_message stores conversation as episodic memory."""
        request = ChatRequest(message="test question")
        await chat_service.handle_message(request)
        mock_memory.create_decision.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_llm_failure_returns_fallback(self, chat_service, mock_llm):
        """LLM failure returns fallback message instead of raising."""
        mock_llm.call.side_effect = RuntimeError("All providers failed")
        request = ChatRequest(message="test")
        response = await chat_service.handle_message(request)
        assert "抱歉" in response.reply
        assert response.metadata.get("fallback") is True

    @pytest.mark.asyncio
    async def test_handle_message_memory_failure_non_fatal(self, chat_service, mock_memory):
        """Memory storage failure doesn't break the response."""
        mock_memory.create_decision.side_effect = Exception("DB error")
        request = ChatRequest(message="test")
        response = await chat_service.handle_message(request)
        assert response.reply == "AI回覆測試"

    @pytest.mark.asyncio
    async def test_handle_message_with_extra_context(self, chat_service, mock_llm):
        """Extra context from request is included in LLM call."""
        request = ChatRequest(message="test", context={"order_id": "ORD-001"})
        await chat_service.handle_message(request)
        call_kwargs = mock_llm.call.call_args
        assert "ORD-001" in call_kwargs.kwargs.get("prompt", "") or "ORD-001" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_privacy_sensitive_message_uses_local(self, mock_db, mock_llm, mock_memory):
        """Messages with PII trigger local LLM preference."""
        service = ChatService(
            db=mock_db,
            llm_router=mock_llm,
            memory_service=mock_memory,
            privacy_guard=PrivacyGuard(),
        )
        # Taiwan national ID triggers high sensitivity
        request = ChatRequest(message="客戶身分證 A123456789")
        await service.handle_message(request)
        call_kwargs = mock_llm.call.call_args
        assert call_kwargs.kwargs.get("prefer_local") is True


# ---------------------------------------------------------------------------
# Suggestion Generation Tests
# ---------------------------------------------------------------------------


class TestSuggestionGeneration:
    """Test ChatService._generate_suggestions."""

    def test_delivery_keywords_generate_suggestions(self):
        """Delivery-related keywords generate appropriate suggestions."""
        suggestions = ChatService._generate_suggestions("這個訂單的交期是什麼時候？")
        assert len(suggestions) > 0
        assert any("排程" in s or "甘特" in s for s in suggestions)

    def test_rush_keywords_generate_suggestions(self):
        """Rush order keywords generate appropriate suggestions."""
        suggestions = ChatService._generate_suggestions("我需要插入一個急單")
        assert any("急單" in s or "模擬" in s for s in suggestions)

    def test_line_keywords_generate_suggestions(self):
        """Production line keywords generate appropriate suggestions."""
        suggestions = ChatService._generate_suggestions("產線A故障了")
        assert any("產線" in s or "排程" in s for s in suggestions)

    def test_default_suggestions_for_generic_message(self):
        """Generic messages still get default suggestions."""
        suggestions = ChatService._generate_suggestions("hello")
        assert len(suggestions) >= 1

    def test_suggestions_capped_at_four(self):
        """Suggestions are limited to 4."""
        suggestions = ChatService._generate_suggestions("交期 急單 產線 排程 故障")
        assert len(suggestions) <= 4


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestChatSchemas:
    """Test ChatRequest/ChatResponse schemas."""

    def test_chat_request_valid(self):
        req = ChatRequest(message="hello")
        assert req.message == "hello"
        assert req.conversation_id is None
        assert req.context == {}

    def test_chat_request_rejects_empty_message(self):
        with pytest.raises(Exception):
            ChatRequest(message="")

    def test_chat_response_defaults(self):
        resp = ChatResponse(reply="hi", conversation_id="c1")
        assert resp.sources == []
        assert resp.suggestions == []
        assert resp.metadata == {}
