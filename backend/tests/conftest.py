"""Pytest configuration with fixtures for async testing."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Test Data Factories (using MagicMock for SQLAlchemy 2.0 compatibility)
# ---------------------------------------------------------------------------


def _make_mock(defaults: dict[str, Any], overrides: dict[str, Any]) -> MagicMock:
    """Create a MagicMock with given attributes."""
    merged = {**defaults, **overrides}
    mock = MagicMock()
    for k, v in merged.items():
        setattr(mock, k, v)
    return mock


class ProductFactory:
    """Factory for creating Product instances for testing."""

    _counter = 0

    @classmethod
    def create(cls, **overrides: Any) -> MagicMock:
        cls._counter += 1
        defaults = {
            "id": uuid.uuid4(),
            "sku": f"SKU-{cls._counter:04d}",
            "name": f"Test Product {cls._counter}",
            "description": "Test product description",
            "standard_cycle_time": 2.0,
            "setup_time": 30.0,
            "yield_rate": 0.95,
            "learned_cycle_time": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        return _make_mock(defaults, overrides)


class ProductionLineFactory:
    """Factory for creating ProductionLine instances for testing."""

    _counter = 0

    @classmethod
    def create(cls, **overrides: Any) -> MagicMock:
        cls._counter += 1
        defaults = {
            "id": uuid.uuid4(),
            "name": f"Line-{cls._counter}",
            "description": f"Test production line {cls._counter}",
            "capacity_per_hour": 100,
            "efficiency_factor": 1.0,
            "status": "active",
            "allowed_products": None,
            "changeover_matrix": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        return _make_mock(defaults, overrides)


class OrderFactory:
    """Factory for creating Order instances for testing."""

    _counter = 0

    @classmethod
    def create(
        cls,
        items: list | None = None,
        **overrides: Any,
    ) -> MagicMock:
        cls._counter += 1
        defaults = {
            "id": uuid.uuid4(),
            "order_no": f"ORD-{cls._counter:04d}",
            "customer_name": f"Customer {cls._counter}",
            "due_date": datetime.now(timezone.utc) + timedelta(days=7),
            "priority": 5,
            "status": "pending",
            "notes": None,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "items": items or [],
        }
        return _make_mock(defaults, overrides)


class OrderItemFactory:
    """Factory for creating OrderItem instances for testing."""

    @classmethod
    def create(cls, product: MagicMock, order_id: uuid.UUID | None = None, **overrides: Any) -> MagicMock:
        defaults = {
            "id": uuid.uuid4(),
            "order_id": order_id or uuid.uuid4(),
            "product_id": product.id,
            "quantity": 100,
            "created_at": datetime.now(timezone.utc),
            "product": product,
        }
        return _make_mock(defaults, overrides)


class ScheduledJobFactory:
    """Factory for creating ScheduledJob instances for testing."""

    @classmethod
    def create(cls, **overrides: Any) -> MagicMock:
        now = datetime.now(timezone.utc)
        defaults = {
            "id": uuid.uuid4(),
            "order_item_id": uuid.uuid4(),
            "production_line_id": uuid.uuid4(),
            "product_id": uuid.uuid4(),
            "planned_start": now,
            "planned_end": now + timedelta(hours=2),
            "quantity": 100,
            "changeover_time": 0.0,
            "status": "planned",
            "notes": None,
            "created_at": now,
            "updated_at": now,
            "product": None,
        }
        return _make_mock(defaults, overrides)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def product_factory():
    """Provide ProductFactory for tests."""
    ProductFactory._counter = 0
    return ProductFactory


@pytest.fixture
def line_factory():
    """Provide ProductionLineFactory for tests."""
    ProductionLineFactory._counter = 0
    return ProductionLineFactory


@pytest.fixture
def order_factory():
    """Provide OrderFactory for tests."""
    OrderFactory._counter = 0
    return OrderFactory


@pytest.fixture
def order_item_factory():
    """Provide OrderItemFactory for tests."""
    return OrderItemFactory


@pytest.fixture
def job_factory():
    """Provide ScheduledJobFactory for tests."""
    return ScheduledJobFactory


@pytest.fixture
def mock_db():
    """Provide a mock AsyncSession for unit tests."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_llm_response():
    """Provide a factory for mock LLM responses."""

    def _make(content: str = "Test response", provider: str = "anthropic", model: str = "claude-sonnet-4-6"):
        return {
            "content": content,
            "provider": provider,
            "model": model,
            "input_tokens": 100,
            "output_tokens": 50,
            "latency_ms": 250.0,
        }

    return _make


@pytest.fixture
def sample_product(product_factory):
    """A single product with standard settings."""
    return product_factory.create(
        sku="WIDGET-A",
        name="Widget A",
        standard_cycle_time=2.0,
        setup_time=30.0,
        yield_rate=0.95,
    )


@pytest.fixture
def sample_line(line_factory):
    """A single active production line."""
    return line_factory.create(
        name="Main Line",
        capacity_per_hour=100,
        status="active",
    )


@pytest.fixture
def sample_order(order_factory, order_item_factory, sample_product):
    """A single order with one item."""
    order = order_factory.create(priority=5)
    item = order_item_factory.create(
        product=sample_product,
        order_id=order.id,
        quantity=100,
    )
    order.items = [item]
    return order


# ---------------------------------------------------------------------------
# Phase 1 Factories: ProcessStation, ProcessRoute, LineCapability
# ---------------------------------------------------------------------------


class ProcessStationFactory:
    """Factory for creating ProcessStation mock instances."""

    _counter = 0

    @classmethod
    def create(cls, **overrides: Any) -> MagicMock:
        cls._counter += 1
        now = datetime.now(timezone.utc)
        defaults = {
            "id": uuid.uuid4(),
            "production_line_id": uuid.uuid4(),
            "name": f"Station-{cls._counter}",
            "station_order": cls._counter,
            "equipment_type": "SMT",
            "standard_cycle_time": 45.0,
            "actual_cycle_time": None,
            "capabilities": None,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        return _make_mock(defaults, overrides)


class ProcessRouteFactory:
    """Factory for creating ProcessRoute mock instances."""

    _counter = 0

    @classmethod
    def create(cls, **overrides: Any) -> MagicMock:
        cls._counter += 1
        now = datetime.now(timezone.utc)
        defaults = {
            "id": uuid.uuid4(),
            "product_id": uuid.uuid4(),
            "version": 1,
            "is_active": True,
            "steps": [
                {"station_order": 1, "equipment_type": "SMT", "cycle_time_sec": 45.0},
                {"station_order": 2, "equipment_type": "reflow", "cycle_time_sec": 120.0},
            ],
            "source": "manual",
            "source_file": None,
            "created_at": now,
            "updated_at": now,
        }
        return _make_mock(defaults, overrides)


class LineCapabilityFactory:
    """Factory for creating LineCapabilityMatrix mock instances."""

    _counter = 0

    @classmethod
    def create(cls, **overrides: Any) -> MagicMock:
        cls._counter += 1
        defaults = {
            "id": uuid.uuid4(),
            "production_line_id": uuid.uuid4(),
            "equipment_type": "SMT",
            "capability_params": None,
            "throughput_range": None,
            "updated_at": datetime.now(timezone.utc),
        }
        return _make_mock(defaults, overrides)


@pytest.fixture
def station_factory():
    """Provide ProcessStationFactory for tests."""
    ProcessStationFactory._counter = 0
    return ProcessStationFactory


@pytest.fixture
def route_factory():
    """Provide ProcessRouteFactory for tests."""
    ProcessRouteFactory._counter = 0
    return ProcessRouteFactory


@pytest.fixture
def capability_factory():
    """Provide LineCapabilityFactory for tests."""
    LineCapabilityFactory._counter = 0
    return LineCapabilityFactory
