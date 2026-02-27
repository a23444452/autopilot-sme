"""Tests for SchedulerService route-based time estimation (Phase 1 addition)."""

import pytest

from app.services.scheduler import SchedulerService


class TestEstimateHoursFromRoute:
    def test_basic_bottleneck_calculation(self):
        steps = [
            {"cycle_time_sec": 45.0},
            {"cycle_time_sec": 120.0},  # bottleneck
        ]
        # 120 sec * 100 units / 60 = 200 min -> 200/60 = 3.333 hours + 0.5 setup
        result = SchedulerService._estimate_hours_from_route(
            steps=steps, quantity=100, yield_rate=1.0, efficiency_factor=1.0, setup_time_min=30.0
        )
        expected = (120.0 * 100 / 60.0) / 60.0 + 30.0 / 60.0
        assert result == pytest.approx(expected)

    def test_with_yield_and_efficiency(self):
        steps = [{"cycle_time_sec": 60.0}]
        # effective_qty = 100 / 0.9 ≈ 111.11
        # prod_time_min = 60 * 111.11 / 0.8 / 60 = 138.89 min
        # hours = 138.89 / 60 + 30/60 = 2.815
        result = SchedulerService._estimate_hours_from_route(
            steps=steps, quantity=100, yield_rate=0.9, efficiency_factor=0.8, setup_time_min=30.0
        )
        expected_prod_min = 60.0 * (100 / 0.9) / 0.8 / 60.0
        expected_hours = expected_prod_min / 60.0 + 30.0 / 60.0
        assert result == pytest.approx(expected_hours)

    def test_zero_setup_time(self):
        steps = [{"cycle_time_sec": 60.0}]
        result = SchedulerService._estimate_hours_from_route(
            steps=steps, quantity=60, yield_rate=1.0, efficiency_factor=1.0, setup_time_min=0.0
        )
        # 60 * 60 / 60 = 60 min -> 1 hour
        assert result == pytest.approx(1.0)

    def test_empty_steps_returns_setup_only(self):
        result = SchedulerService._estimate_hours_from_route(
            steps=[], quantity=100, yield_rate=1.0, efficiency_factor=1.0, setup_time_min=30.0
        )
        assert result == pytest.approx(0.5)

    def test_uses_actual_cycle_time(self):
        steps = [
            {"cycle_time_sec": 60.0, "actual_cycle_time_sec": 90.0},
        ]
        result = SchedulerService._estimate_hours_from_route(
            steps=steps, quantity=60, yield_rate=1.0, efficiency_factor=1.0, setup_time_min=0.0
        )
        # bottleneck = 90, 90 * 60 / 60 = 90 min -> 1.5 hours
        assert result == pytest.approx(1.5)
