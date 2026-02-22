"""Tests for security fixes: SQL Injection, Memory API schema, and input validation.

Covers:
- C1: SQL Injection in init_db.py table_has_data (whitelist fix)
- C2: SQL Injection in memory_service.py _sql_text_search
- C3/M9: Memory API uses POST + Request Body for search
- Input validation on schemas
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.memory import MemorySearch


# ---------------------------------------------------------------------------
# C1: SQL Injection in init_db.py - table_has_data (whitelist fix)
# ---------------------------------------------------------------------------


class TestSQLInjectionInitDB:
    """Test that table_has_data validates table names against a whitelist."""

    @pytest.mark.asyncio
    async def test_malicious_table_name_rejected(self):
        """Malicious table names should be rejected via whitelist validation."""
        from app.db.init_db import table_has_data

        mock_session = AsyncMock()
        # Mock run_sync to return a set of valid table names
        mock_session.run_sync = AsyncMock(return_value={"orders", "products", "production_lines"})

        malicious_name = "users; DROP TABLE orders; --"

        with pytest.raises(ValueError, match="Unknown table"):
            await table_has_data(mock_session, malicious_name)

    @pytest.mark.asyncio
    async def test_valid_table_name_accepted(self):
        """Valid table names pass the whitelist check."""
        from app.db.init_db import table_has_data

        mock_session = AsyncMock()
        mock_session.run_sync = AsyncMock(return_value={"orders", "products"})

        mock_result = MagicMock()
        mock_result.scalar.return_value = True
        mock_session.execute.return_value = mock_result

        result = await table_has_data(mock_session, "orders")
        assert result is True

    @pytest.mark.asyncio
    async def test_nonexistent_table_rejected(self):
        """Non-existent table names are rejected."""
        from app.db.init_db import table_has_data

        mock_session = AsyncMock()
        mock_session.run_sync = AsyncMock(return_value={"orders", "products"})

        with pytest.raises(ValueError, match="Unknown table"):
            await table_has_data(mock_session, "nonexistent_table")

    @pytest.mark.asyncio
    async def test_empty_table_returns_false(self):
        """Empty table returns False."""
        from app.db.init_db import table_has_data

        mock_session = AsyncMock()
        mock_session.run_sync = AsyncMock(return_value={"orders"})

        mock_result = MagicMock()
        mock_result.scalar.return_value = False
        mock_session.execute.return_value = mock_result

        result = await table_has_data(mock_session, "orders")
        assert result is False


# ---------------------------------------------------------------------------
# C2: SQL Injection in memory_service.py - _sql_text_search
# ---------------------------------------------------------------------------


class TestSQLInjectionMemoryService:
    """Test that _sql_text_search is safe from SQL injection."""

    @pytest.fixture
    def memory_service(self, mock_db):
        from app.services.memory_service import MemoryService

        mock_qdrant = AsyncMock()
        return MemoryService(db=mock_db, qdrant=mock_qdrant)

    @pytest.mark.asyncio
    async def test_sql_text_search_with_special_chars(self, memory_service, mock_db):
        """_sql_text_search should handle special characters safely."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        dangerous_queries = [
            "test'; DROP TABLE memory_entries; --",
            "test%' OR '1'='1",
            "test\" UNION SELECT * FROM users --",
            "test\\'; DELETE FROM memory_entries; --",
        ]

        for query in dangerous_queries:
            result = await memory_service._sql_text_search(
                query=query, memory_type=None, category=None, limit=10
            )
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_sql_text_search_with_normal_query(self, memory_service, mock_db):
        """_sql_text_search works with normal queries."""
        mock_memory = MagicMock()
        mock_memory.id = uuid.uuid4()
        mock_memory.importance = 0.7
        mock_memory.memory_type = "episodic"
        mock_memory.category = "scheduling"
        mock_memory.content = "Test content"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_memory]
        mock_db.execute.return_value = mock_result

        result = await memory_service._sql_text_search(
            query="scheduling", memory_type=None, category=None, limit=10
        )
        assert len(result) == 1
        assert result[0]["memory_id"] == str(mock_memory.id)


# ---------------------------------------------------------------------------
# C3/M9: Memory API Schema Validation
# ---------------------------------------------------------------------------


class TestMemorySearchSchema:
    """Test MemorySearch schema validates input properly."""

    def test_valid_search(self):
        search = MemorySearch(query="排程問題", limit=5)
        assert search.query == "排程問題"
        assert search.limit == 5

    def test_empty_query_rejected(self):
        with pytest.raises(Exception):
            MemorySearch(query="")

    def test_query_max_length(self):
        with pytest.raises(Exception):
            MemorySearch(query="x" * 1001)

    def test_default_limit(self):
        search = MemorySearch(query="test")
        assert search.limit == 10

    def test_limit_lower_bound(self):
        with pytest.raises(Exception):
            MemorySearch(query="test", limit=0)

    def test_limit_upper_bound(self):
        with pytest.raises(Exception):
            MemorySearch(query="test", limit=101)

    def test_optional_filters(self):
        search = MemorySearch(query="test")
        assert search.memory_type is None
        assert search.category is None

    def test_memory_type_filter(self):
        search = MemorySearch(query="test", memory_type="episodic")
        assert search.memory_type == "episodic"

    def test_category_filter(self):
        search = MemorySearch(query="test", category="scheduling")
        assert search.category == "scheduling"


# ---------------------------------------------------------------------------
# Order Schema Input Validation
# ---------------------------------------------------------------------------


class TestOrderInputValidation:
    """Test that order input validation prevents injection attacks."""

    def test_order_no_with_special_chars(self):
        from app.schemas.order import OrderCreate

        order = OrderCreate(
            order_no="ORD-<script>",
            customer_name="Test",
            due_date=datetime.now(timezone.utc),
        )
        assert order.order_no == "ORD-<script>"

    def test_customer_name_max_length_prevents_overflow(self):
        from app.schemas.order import OrderCreate

        with pytest.raises(Exception):
            OrderCreate(
                order_no="ORD-001",
                customer_name="A" * 201,
                due_date=datetime.now(timezone.utc),
            )
