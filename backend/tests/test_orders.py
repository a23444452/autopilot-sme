"""Tests for Orders CRUD operations and validation."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.order import OrderCreate, OrderItemCreate


# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------


class TestOrderSchemaValidation:
    """Test OrderCreate schema validation rules."""

    def test_valid_order_create(self):
        """OrderCreate accepts valid data."""
        order = OrderCreate(
            order_no="ORD-001",
            customer_name="Test Customer",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            priority=5,
            items=[],
        )
        assert order.order_no == "ORD-001"
        assert order.priority == 5

    def test_order_default_priority(self):
        """OrderCreate defaults priority to 5."""
        order = OrderCreate(
            order_no="ORD-002",
            customer_name="Customer",
            due_date=datetime.now(timezone.utc),
        )
        assert order.priority == 5

    def test_order_priority_lower_bound(self):
        """OrderCreate rejects priority < 1."""
        with pytest.raises(Exception):
            OrderCreate(
                order_no="ORD-003",
                customer_name="Customer",
                due_date=datetime.now(timezone.utc),
                priority=0,
            )

    def test_order_priority_upper_bound(self):
        """OrderCreate rejects priority > 10."""
        with pytest.raises(Exception):
            OrderCreate(
                order_no="ORD-004",
                customer_name="Customer",
                due_date=datetime.now(timezone.utc),
                priority=11,
            )

    def test_order_with_items(self):
        """OrderCreate can include line items."""
        product_id = uuid.uuid4()
        order = OrderCreate(
            order_no="ORD-005",
            customer_name="Customer",
            due_date=datetime.now(timezone.utc),
            items=[OrderItemCreate(product_id=product_id, quantity=50)],
        )
        assert len(order.items) == 1
        assert order.items[0].quantity == 50

    def test_order_item_quantity_must_be_positive(self):
        """OrderItemCreate rejects quantity <= 0."""
        with pytest.raises(Exception):
            OrderItemCreate(product_id=uuid.uuid4(), quantity=0)

    def test_order_no_max_length(self):
        """OrderCreate rejects order_no exceeding 50 chars."""
        with pytest.raises(Exception):
            OrderCreate(
                order_no="X" * 51,
                customer_name="Customer",
                due_date=datetime.now(timezone.utc),
            )

    def test_order_customer_name_max_length(self):
        """OrderCreate rejects customer_name exceeding 200 chars."""
        with pytest.raises(Exception):
            OrderCreate(
                order_no="ORD-006",
                customer_name="X" * 201,
                due_date=datetime.now(timezone.utc),
            )

    def test_order_notes_optional(self):
        """OrderCreate allows notes to be None."""
        order = OrderCreate(
            order_no="ORD-007",
            customer_name="Customer",
            due_date=datetime.now(timezone.utc),
        )
        assert order.notes is None

    def test_order_items_default_empty(self):
        """OrderCreate defaults items to empty list."""
        order = OrderCreate(
            order_no="ORD-008",
            customer_name="Customer",
            due_date=datetime.now(timezone.utc),
        )
        assert order.items == []


# ---------------------------------------------------------------------------
# Order Model / Factory Tests
# ---------------------------------------------------------------------------


class TestOrderFactory:
    """Test order creation through factories."""

    def test_create_order_with_defaults(self, order_factory):
        """Factory creates order with sensible defaults."""
        order = order_factory.create()
        assert order.id is not None
        assert order.order_no.startswith("ORD-")
        assert order.status == "pending"
        assert order.priority == 5

    def test_create_order_with_items(self, order_factory, order_item_factory, product_factory):
        """Factory creates order with attached items."""
        product = product_factory.create()
        order = order_factory.create()
        item = order_item_factory.create(product=product, order_id=order.id, quantity=200)
        object.__setattr__(order, "items", [item])

        assert len(order.items) == 1
        assert order.items[0].quantity == 200
        assert order.items[0].product.sku == product.sku

    def test_create_order_custom_priority(self, order_factory):
        """Factory respects custom priority override."""
        order = order_factory.create(priority=1)
        assert order.priority == 1

    def test_create_order_custom_status(self, order_factory):
        """Factory respects custom status override."""
        order = order_factory.create(status="confirmed")
        assert order.status == "confirmed"


# ---------------------------------------------------------------------------
# Order Filtering Logic Tests
# ---------------------------------------------------------------------------


class TestOrderFiltering:
    """Test order filtering/query logic."""

    def test_orders_have_unique_order_numbers(self, order_factory):
        """Each factory-created order has a unique order_no."""
        orders = [order_factory.create() for _ in range(5)]
        order_nos = [o.order_no for o in orders]
        assert len(set(order_nos)) == 5

    def test_filter_by_status(self, order_factory):
        """Orders can be filtered by status."""
        orders = [
            order_factory.create(status="pending"),
            order_factory.create(status="confirmed"),
            order_factory.create(status="completed"),
        ]
        pending = [o for o in orders if o.status == "pending"]
        assert len(pending) == 1

    def test_filter_by_due_date_range(self, order_factory):
        """Orders can be filtered by due date range."""
        now = datetime.now(timezone.utc)
        orders = [
            order_factory.create(due_date=now - timedelta(days=1)),
            order_factory.create(due_date=now + timedelta(days=3)),
            order_factory.create(due_date=now + timedelta(days=10)),
        ]
        start = now
        end = now + timedelta(days=7)
        in_range = [o for o in orders if start <= o.due_date <= end]
        assert len(in_range) == 1

    def test_sort_by_priority(self, order_factory):
        """Orders can be sorted by priority (ascending)."""
        orders = [
            order_factory.create(priority=8),
            order_factory.create(priority=1),
            order_factory.create(priority=5),
        ]
        sorted_orders = sorted(orders, key=lambda o: o.priority)
        assert sorted_orders[0].priority == 1
        assert sorted_orders[-1].priority == 8
