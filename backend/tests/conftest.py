"""Pytest configuration with fixtures for async testing."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.production_line import ProductionLine
from app.models.schedule import ScheduledJob


# ---------------------------------------------------------------------------
# Test Data Factories
# ---------------------------------------------------------------------------


class ProductFactory:
    """Factory for creating Product instances for testing."""

    _counter = 0

    @classmethod
    def create(cls, **overrides: Any) -> Product:
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
        defaults.update(overrides)
        product = Product.__new__(Product)
        for k, v in defaults.items():
            object.__setattr__(product, k, v)
        return product


class ProductionLineFactory:
    """Factory for creating ProductionLine instances for testing."""

    _counter = 0

    @classmethod
    def create(cls, **overrides: Any) -> ProductionLine:
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
        defaults.update(overrides)
        line = ProductionLine.__new__(ProductionLine)
        for k, v in defaults.items():
            object.__setattr__(line, k, v)
        return line


class OrderFactory:
    """Factory for creating Order instances for testing."""

    _counter = 0

    @classmethod
    def create(
        cls,
        items: list[OrderItem] | None = None,
        **overrides: Any,
    ) -> Order:
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
        }
        defaults.update(overrides)
        order = Order.__new__(Order)
        for k, v in defaults.items():
            object.__setattr__(order, k, v)
        object.__setattr__(order, "items", items or [])
        return order


class OrderItemFactory:
    """Factory for creating OrderItem instances for testing."""

    @classmethod
    def create(cls, product: Product, order_id: uuid.UUID | None = None, **overrides: Any) -> OrderItem:
        defaults = {
            "id": uuid.uuid4(),
            "order_id": order_id or uuid.uuid4(),
            "product_id": product.id,
            "quantity": 100,
            "created_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        item = OrderItem.__new__(OrderItem)
        for k, v in defaults.items():
            object.__setattr__(item, k, v)
        object.__setattr__(item, "product", product)
        return item


class ScheduledJobFactory:
    """Factory for creating ScheduledJob instances for testing."""

    @classmethod
    def create(cls, **overrides: Any) -> ScheduledJob:
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
        }
        defaults.update(overrides)
        job = ScheduledJob.__new__(ScheduledJob)
        for k, v in defaults.items():
            object.__setattr__(job, k, v)
        # Default: no product relationship loaded
        if "product" not in overrides:
            object.__setattr__(job, "product", None)
        return job


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
    object.__setattr__(order, "items", [item])
    return order
