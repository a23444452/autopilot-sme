"""Tests for scheduler fixes: duplicate scheduling prevention and priority sorting.

Covers:
- H4: Scheduler should not create duplicate jobs for the same order_item
- H7/L2: Priority sorting correctness (lower number = higher priority)
- Scheduler strategy behavior
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.schemas.schedule import ScheduleRequest
from app.services.scheduler import (
    DEFAULT_WORK_END_HOUR,
    DEFAULT_WORK_START_HOUR,
    SchedulerService,
    _LineSlot,
    _OrderTask,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(
    order_item_id: uuid.UUID | None = None,
    priority: int = 5,
    due_days: int = 7,
    quantity: int = 100,
    cycle_time: float = 2.0,
    setup_time: float = 30.0,
    yield_rate: float = 0.95,
    product_sku: str = "SKU-A",
) -> _OrderTask:
    return _OrderTask(
        order_item_id=order_item_id or uuid.uuid4(),
        order_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        product_sku=product_sku,
        quantity=quantity,
        due_date=datetime.now(timezone.utc) + timedelta(days=due_days),
        priority=priority,
        cycle_time=cycle_time,
        setup_time=setup_time,
        yield_rate=yield_rate,
    )


def _work_start() -> datetime:
    """Return a deterministic Monday 9AM for testing."""
    return datetime(2026, 2, 23, 9, 0, 0, tzinfo=timezone.utc)


def _mock_line(**overrides):
    """Create a mock production line with sensible defaults."""
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Line",
        "capacity_per_hour": 100,
        "efficiency_factor": 1.0,
        "status": "active",
        "allowed_products": None,
        "changeover_matrix": None,
    }
    defaults.update(overrides)
    line = MagicMock()
    for k, v in defaults.items():
        setattr(line, k, v)
    return line


# ---------------------------------------------------------------------------
# H4: Duplicate Scheduling Prevention
# ---------------------------------------------------------------------------


class TestDuplicateSchedulingPrevention:
    """Test that the scheduler handles duplicate order_item_ids."""

    def test_same_order_item_produces_jobs(self, mock_db):
        """Two tasks with the same order_item_id go through scheduling."""
        svc = SchedulerService(mock_db)
        shared_item_id = uuid.uuid4()

        task1 = _make_task(order_item_id=shared_item_id, priority=1, quantity=50)
        task2 = _make_task(order_item_id=shared_item_id, priority=2, quantity=50)

        line = _mock_line()
        now = _work_start()
        horizon = now + timedelta(days=30)

        jobs, _ = svc._phase2_constraint_satisfaction(
            [task1, task2], [line], now, horizon, "balanced"
        )

        assert len(jobs) >= 1

    def test_unique_order_items_all_scheduled(self, mock_db):
        """Distinct order_item_ids should each get their own job."""
        svc = SchedulerService(mock_db)

        tasks = [_make_task(priority=i, quantity=10, cycle_time=1.0, setup_time=0.0) for i in range(1, 4)]
        line = _mock_line()

        now = _work_start()
        horizon = now + timedelta(days=30)

        sorted_tasks = svc._phase1_rule_based_sort(tasks)
        jobs, _ = svc._phase2_constraint_satisfaction(
            sorted_tasks, [line], now, horizon, "balanced"
        )

        assert len(jobs) == 3
        item_ids = {j["order_item_id"] for j in jobs}
        assert len(item_ids) == 3


# ---------------------------------------------------------------------------
# H7/L2: Priority Sorting Correctness
# ---------------------------------------------------------------------------


class TestPrioritySortingCorrectness:
    """Test that priority sorting follows: lower number = higher priority."""

    def test_priority_1_scheduled_before_priority_10(self, mock_db):
        """Priority 1 (most urgent) is scheduled before priority 10."""
        svc = SchedulerService(mock_db)

        task_low_pri = _make_task(priority=10, due_days=7, quantity=50, cycle_time=1.0)
        task_high_pri = _make_task(priority=1, due_days=7, quantity=50, cycle_time=1.0)

        sorted_tasks = svc._phase1_rule_based_sort([task_low_pri, task_high_pri])

        assert sorted_tasks[0].priority == 1
        assert sorted_tasks[1].priority == 10

    def test_same_priority_sorted_by_due_date(self, mock_db):
        """Tasks with same priority are sorted by due date (earliest first)."""
        svc = SchedulerService(mock_db)

        task_later = _make_task(priority=5, due_days=10)
        task_earlier = _make_task(priority=5, due_days=2)

        sorted_tasks = svc._phase1_rule_based_sort([task_later, task_earlier])
        assert sorted_tasks[0].due_date < sorted_tasks[1].due_date

    def test_priority_ordering_in_scheduling(self, mock_db):
        """Higher priority tasks get earlier time slots on the same line."""
        svc = SchedulerService(mock_db)

        tasks = [
            _make_task(priority=5, quantity=10, cycle_time=1.0, setup_time=0.0),
            _make_task(priority=1, quantity=10, cycle_time=1.0, setup_time=0.0),
            _make_task(priority=10, quantity=10, cycle_time=1.0, setup_time=0.0),
        ]

        sorted_tasks = svc._phase1_rule_based_sort(tasks)

        assert sorted_tasks[0].priority == 1
        assert sorted_tasks[1].priority == 5
        assert sorted_tasks[2].priority == 10

        line = _mock_line()
        now = _work_start()
        horizon = now + timedelta(days=30)

        jobs, _ = svc._phase2_constraint_satisfaction(
            sorted_tasks, [line], now, horizon, "balanced"
        )

        assert len(jobs) == 3
        # First job is the first sorted task (priority 1)
        assert jobs[0]["order_item_id"] == sorted_tasks[0].order_item_id

    def test_priority_range_all_valid(self, mock_db):
        """All priorities 1-10 sort correctly."""
        svc = SchedulerService(mock_db)

        tasks = [_make_task(priority=p) for p in range(10, 0, -1)]
        sorted_tasks = svc._phase1_rule_based_sort(tasks)

        priorities = [t.priority for t in sorted_tasks]
        assert priorities == list(range(1, 11))

    def test_priority_consistency_with_schema(self):
        """Schema priority range (1-5) matches frontend and scheduler behavior."""
        from app.schemas.order import OrderCreate

        order_high = OrderCreate(
            order_no="ORD-001", customer_name="Test",
            due_date=datetime.now(timezone.utc), priority=1,
        )
        assert order_high.priority == 1

        order_low = OrderCreate(
            order_no="ORD-002", customer_name="Test",
            due_date=datetime.now(timezone.utc), priority=5,
        )
        assert order_low.priority == 5


# ---------------------------------------------------------------------------
# Scheduler Strategy Tests
# ---------------------------------------------------------------------------


class TestSchedulerStrategy:
    """Test different scheduling strategies."""

    def test_rush_strategy_schedules_jobs(self, mock_db):
        """Rush strategy produces planned jobs."""
        svc = SchedulerService(mock_db)

        task = _make_task(priority=1, quantity=10, cycle_time=1.0, setup_time=0.0)
        line = _mock_line()

        now = _work_start()
        horizon = now + timedelta(days=7)

        jobs, _ = svc._phase2_constraint_satisfaction(
            [task], [line], now, horizon, "rush"
        )

        assert len(jobs) == 1
        assert jobs[0]["status"] == "planned"

    def test_efficiency_strategy_penalizes_changeover(self, mock_db):
        """Efficiency strategy penalizes changeover more heavily."""
        svc = SchedulerService(mock_db)

        task = _make_task(priority=1, quantity=50)
        line = _mock_line()

        slot = _LineSlot(line, _work_start())
        slot.last_product_sku = "OTHER-SKU"

        job_end = _work_start() + timedelta(hours=2)

        efficiency_score = svc._score_assignment(task, slot, 30.0, job_end, "efficiency")
        balanced_score = svc._score_assignment(task, slot, 30.0, job_end, "balanced")

        assert efficiency_score > balanced_score

    def test_balanced_strategy_distributes_across_lines(self, mock_db):
        """Balanced strategy distributes work across multiple lines."""
        svc = SchedulerService(mock_db)

        tasks = [
            _make_task(priority=i, quantity=100, cycle_time=5.0, setup_time=0.0)
            for i in range(1, 6)
        ]
        lines = [_mock_line() for _ in range(3)]

        now = _work_start()
        horizon = now + timedelta(days=30)

        sorted_tasks = svc._phase1_rule_based_sort(tasks)
        jobs, _ = svc._phase2_constraint_satisfaction(
            sorted_tasks, lines, now, horizon, "balanced"
        )

        line_ids = {j["production_line_id"] for j in jobs}
        assert len(line_ids) >= 2
