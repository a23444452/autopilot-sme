"""Tests for MemoryService: decision records CRUD, importance scoring, lifecycle management."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.memory_service import MemoryService, HOT_THRESHOLD_DAYS, WARM_THRESHOLD_DAYS


# ---------------------------------------------------------------------------
# Importance Scoring Tests
# ---------------------------------------------------------------------------


class TestImportanceScoring:
    """Test MemoryService._score_importance static method."""

    def test_base_score_for_short_content(self):
        """Short generic content gets base score."""
        score = MemoryService._score_importance("hello", "chat")
        assert score == 0.5

    def test_long_content_boost(self):
        """Content over 500 chars gets +0.1 boost."""
        long_text = "x" * 501
        score = MemoryService._score_importance(long_text, "chat")
        assert score == pytest.approx(0.6, abs=0.01)

    def test_medium_content_boost(self):
        """Content 200-500 chars gets +0.05 boost."""
        medium_text = "x" * 201
        score = MemoryService._score_importance(medium_text, "chat")
        assert score == pytest.approx(0.55, abs=0.01)

    def test_scheduling_category_weight(self):
        """Scheduling category adds 0.15."""
        score = MemoryService._score_importance("test", "scheduling")
        assert score == pytest.approx(0.65, abs=0.01)

    def test_rush_order_category_weight(self):
        """Rush order category adds 0.2."""
        score = MemoryService._score_importance("test", "rush_order")
        assert score == pytest.approx(0.7, abs=0.01)

    def test_exception_category_weight(self):
        """Exception category adds 0.2."""
        score = MemoryService._score_importance("test", "exception")
        assert score == pytest.approx(0.7, abs=0.01)

    def test_keyword_boost_urgent(self):
        """Keyword 'urgent' adds 0.05."""
        score = MemoryService._score_importance("this is urgent", "chat")
        assert score == pytest.approx(0.55, abs=0.01)

    def test_keyword_boost_chinese(self):
        """Chinese keyword '緊急' adds 0.05."""
        score = MemoryService._score_importance("這是緊急訂單", "chat")
        assert score == pytest.approx(0.55, abs=0.01)

    def test_multiple_keywords_stack(self):
        """Multiple keywords each add 0.05."""
        score = MemoryService._score_importance("urgent rush failure", "chat")
        assert score == pytest.approx(0.65, abs=0.01)

    def test_score_capped_at_one(self):
        """Score never exceeds 1.0."""
        text = "urgent rush failure exception delay 緊急 趕工 故障 異常 延遲 " + "x" * 600
        score = MemoryService._score_importance(text, "rush_order")
        assert score <= 1.0

    def test_unknown_category_no_weight(self):
        """Unknown category adds 0.0."""
        score = MemoryService._score_importance("test", "unknown_category")
        assert score == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# Decision CRUD Tests (mocked DB + Qdrant)
# ---------------------------------------------------------------------------


class TestDecisionCRUD:
    """Test MemoryService decision record operations with mocked dependencies."""

    @pytest.fixture
    def memory_service(self, mock_db):
        """MemoryService with mocked DB and Qdrant."""
        mock_qdrant = AsyncMock()
        mock_embedding = AsyncMock()
        mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)
        mock_qdrant.upsert = AsyncMock()
        svc = MemoryService(db=mock_db, qdrant=mock_qdrant, embedding_service=mock_embedding)
        return svc

    @pytest.mark.asyncio
    async def test_create_decision_adds_to_db(self, memory_service, mock_db):
        """create_decision adds DecisionLog and MemoryEntry to session."""
        await memory_service.create_decision(
            decision_type="scheduling",
            situation="Rush order arrived",
        )
        # Should call db.add twice (DecisionLog + MemoryEntry)
        assert mock_db.add.call_count == 2
        assert mock_db.flush.call_count >= 2

    @pytest.mark.asyncio
    async def test_create_decision_stores_embedding(self, memory_service):
        """create_decision stores embedding in Qdrant."""
        await memory_service.create_decision(
            decision_type="scheduling",
            situation="Test situation",
        )
        memory_service.qdrant.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_decision_returns_result(self, memory_service, mock_db):
        """get_decision executes a select query."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await memory_service.get_decision(uuid.uuid4())
        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_decisions_with_type_filter(self, memory_service, mock_db):
        """list_decisions filters by decision_type when provided."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await memory_service.list_decisions(decision_type="scheduling")
        assert result == []
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_decision_outcome(self, memory_service, mock_db):
        """update_decision_outcome updates outcome and lessons_learned."""
        # Mock get_decision to return a decision
        mock_decision = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_decision
        mock_db.execute.return_value = mock_result

        result = await memory_service.update_decision_outcome(
            decision_id=uuid.uuid4(),
            outcome={"result": "success"},
            lessons_learned="It worked well",
        )
        assert result is mock_decision
        assert mock_decision.outcome == {"result": "success"}
        assert mock_decision.lessons_learned == "It worked well"


# ---------------------------------------------------------------------------
# Memory Entry CRUD Tests
# ---------------------------------------------------------------------------


class TestMemoryCRUD:
    """Test MemoryService memory entry operations."""

    @pytest.fixture
    def memory_service(self, mock_db):
        mock_qdrant = AsyncMock()
        mock_embedding = AsyncMock()
        mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 1536)
        mock_qdrant.upsert = AsyncMock()
        return MemoryService(db=mock_db, qdrant=mock_qdrant, embedding_service=mock_embedding)

    @pytest.mark.asyncio
    async def test_create_memory_episodic_stores_embedding(self, memory_service):
        """Episodic memories get stored in Qdrant."""
        await memory_service.create_memory(
            memory_type="episodic",
            category="test",
            content="Test memory content",
        )
        memory_service.qdrant.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_memory_structured_no_embedding(self, memory_service):
        """Structured memories do NOT get stored in Qdrant."""
        await memory_service.create_memory(
            memory_type="structured",
            category="test",
            content="Test structured memory",
        )
        memory_service.qdrant.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_memory_updates_access_tracking(self, memory_service, mock_db):
        """get_memory increments access_count and updates last_accessed_at."""
        mock_memory = MagicMock()
        mock_memory.access_count = 0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_memory
        mock_db.execute.return_value = mock_result

        result = await memory_service.get_memory(uuid.uuid4())
        assert result is mock_memory
        assert mock_memory.access_count == 1
        assert mock_memory.last_accessed_at is not None


# ---------------------------------------------------------------------------
# Lifecycle Management Tests
# ---------------------------------------------------------------------------


class TestLifecycleManagement:
    """Test memory lifecycle transitions."""

    @pytest.fixture
    def memory_service(self, mock_db):
        mock_qdrant = AsyncMock()
        return MemoryService(db=mock_db, qdrant=mock_qdrant)

    @pytest.mark.asyncio
    async def test_lifecycle_returns_counts(self, memory_service, mock_db):
        """run_lifecycle_transitions returns transition counts."""
        # Mock the two update queries
        mock_hot_result = MagicMock()
        mock_hot_result.scalar.return_value = 3
        mock_cold_result = MagicMock()
        mock_cold_result.scalar.return_value = 1
        mock_db.execute.side_effect = [mock_hot_result, mock_cold_result]

        result = await memory_service.run_lifecycle_transitions()
        assert result == {"hot_to_warm": 3, "warm_to_cold": 1}

    @pytest.mark.asyncio
    async def test_lifecycle_zero_transitions(self, memory_service, mock_db):
        """run_lifecycle_transitions returns zeros when nothing transitions."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await memory_service.run_lifecycle_transitions()
        assert result == {"hot_to_warm": 0, "warm_to_cold": 0}

    def test_hot_threshold_is_7_days(self):
        """Hot threshold is 7 days."""
        assert HOT_THRESHOLD_DAYS == 7

    def test_warm_threshold_is_90_days(self):
        """Warm threshold is 90 days."""
        assert WARM_THRESHOLD_DAYS == 90
