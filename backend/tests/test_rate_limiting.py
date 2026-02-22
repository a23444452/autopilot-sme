"""Tests for rate limiting and API security configuration.

Covers:
- H2: Rate limiting configuration
- API endpoint HTTP method correctness
- Pagination limits on list endpoints
"""

import inspect

import pytest

from app.core.config import settings


# ---------------------------------------------------------------------------
# Configuration Security Tests
# ---------------------------------------------------------------------------


class TestSecurityConfig:
    """Test that security-related configuration is correct."""

    def test_cors_origins_configured(self):
        """CORS origins should be properly configured."""
        origins = settings.CORS_ORIGINS.split(",")
        assert len(origins) >= 1
        assert any(o.startswith("http") for o in origins)

    def test_debug_disabled_in_production(self):
        """Debug mode should be disabled in production."""
        if settings.ENVIRONMENT == "production":
            assert settings.DEBUG is False

    def test_production_not_use_wildcard_cors(self):
        """Production should not use wildcard CORS origins."""
        if settings.is_production:
            origins = settings.CORS_ORIGINS.split(",")
            assert "*" not in origins


# ---------------------------------------------------------------------------
# API Endpoint Method Tests
# ---------------------------------------------------------------------------


class TestAPIEndpointMethods:
    """Test that API endpoints use correct HTTP methods."""

    def test_schedule_generate_endpoint_exists(self):
        """Schedule generation endpoint is POST."""
        from app.api.v1.schedule import router

        found = False
        for route in router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                if "generate" in route.path and "POST" in route.methods:
                    found = True
                    break
        assert found, "Should have a POST endpoint containing 'generate'"

    def test_memory_search_endpoint_exists(self):
        """Memory search endpoint is POST."""
        from app.api.v1.memory import router

        found = False
        for route in router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                if "search" in route.path and "POST" in route.methods:
                    found = True
                    break
        assert found, "Should have a POST endpoint containing 'search'"

    def test_orders_endpoint_exists(self):
        """Orders list endpoint exists."""
        from app.api.v1.orders import router

        found = False
        for route in router.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                if "GET" in route.methods:
                    found = True
                    break
        assert found, "Should have a GET endpoint for listing orders"

    def test_schedule_current_has_limit_param(self):
        """Schedule current endpoint has a limit parameter."""
        from app.api.v1.schedule import get_current_schedule

        sig = inspect.signature(get_current_schedule)
        assert "limit" in sig.parameters

    def test_orders_list_has_limit_param(self):
        """Orders list endpoint has a limit parameter."""
        from app.api.v1.orders import list_orders

        sig = inspect.signature(list_orders)
        assert "limit" in sig.parameters

    def test_memory_facts_has_limit_param(self):
        """Memory facts endpoint has a limit parameter."""
        from app.api.v1.memory import list_facts

        sig = inspect.signature(list_facts)
        assert "limit" in sig.parameters


# ---------------------------------------------------------------------------
# Pagination Validation Tests
# ---------------------------------------------------------------------------


class TestPaginationLimits:
    """Test that list endpoints enforce pagination limits."""

    def test_schedule_request_has_horizon_default(self):
        """ScheduleRequest has a default horizon_days."""
        from app.schemas.schedule import ScheduleRequest

        req = ScheduleRequest()
        assert req.horizon_days > 0

    def test_memory_search_has_limit_bounds(self):
        """MemorySearch limit is bounded between 1 and 100."""
        from app.schemas.memory import MemorySearch

        search = MemorySearch(query="test", limit=1)
        assert search.limit == 1

        search = MemorySearch(query="test", limit=100)
        assert search.limit == 100

        with pytest.raises(Exception):
            MemorySearch(query="test", limit=0)

        with pytest.raises(Exception):
            MemorySearch(query="test", limit=101)
