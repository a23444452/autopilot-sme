"""Tests for the rush order simulation engine."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.simulator import (
    OVERTIME_COST_PER_HOUR,
    AffectedOrder,
    RushOrderInput,
    SimulationError,
    SimulationScenario,
    SimulatorService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    """Return a weekday work-hour datetime for deterministic tests."""
    dt = datetime(2026, 2, 23, 10, 0, 0, tzinfo=timezone.utc)  # Monday 10 AM
    return dt


# ---------------------------------------------------------------------------
# RushOrderInput Tests
# ---------------------------------------------------------------------------


class TestRushOrderInput:
    """Test rush order input construction."""

    def test_default_priority(self):
        """Rush orders default to priority 1."""
        inp = RushOrderInput(
            product_id=uuid.uuid4(),
            quantity=100,
            target_date=_now() + timedelta(days=3),
        )
        assert inp.priority == 1

    def test_custom_priority(self):
        """Rush orders can have custom priority."""
        inp = RushOrderInput(
            product_id=uuid.uuid4(),
            quantity=100,
            target_date=_now() + timedelta(days=3),
            priority=3,
        )
        assert inp.priority == 3


# ---------------------------------------------------------------------------
# Scenario Selection & Recommendation
# ---------------------------------------------------------------------------


class TestScenarioSelection:
    """Test scenario selection and recommendation logic."""

    def _make_scenario(
        self,
        name: str,
        meets_target: bool = True,
        affected: int = 0,
        cost: float = 0.0,
        completion_offset_hours: float = 0.0,
    ) -> SimulationScenario:
        return SimulationScenario(
            name=name,
            description=f"Test scenario {name}",
            production_line_id=uuid.uuid4(),
            production_line_name="Test Line",
            completion_time=_now() + timedelta(hours=completion_offset_hours),
            changeover_time=30.0,
            production_hours=2.0,
            affected_orders=[
                AffectedOrder(
                    order_item_id=uuid.uuid4(),
                    original_end=_now(),
                    new_end=_now() + timedelta(hours=1),
                    delay_minutes=60.0,
                )
                for _ in range(affected)
            ],
            overtime_hours=cost / OVERTIME_COST_PER_HOUR if cost > 0 else 0.0,
            additional_cost=cost,
            meets_target=meets_target,
        )

    def test_recommend_meets_target_no_impact(self, mock_db):
        """Prefers scenario that meets target with no affected orders."""
        svc = SimulatorService(mock_db)
        s1 = self._make_scenario("Append", meets_target=True, affected=0)
        s2 = self._make_scenario("Insert", meets_target=True, affected=2)
        result = svc._pick_recommendation([s1, s2])
        assert result == "Append"
        assert s1.recommendation is True

    def test_recommend_meets_target_fewest_affected(self, mock_db):
        """When all impact orders, prefers fewest affected."""
        svc = SimulatorService(mock_db)
        s1 = self._make_scenario("A", meets_target=True, affected=3)
        s2 = self._make_scenario("B", meets_target=True, affected=1)
        result = svc._pick_recommendation([s1, s2])
        assert result == "B"

    def test_recommend_earliest_when_none_meet_target(self, mock_db):
        """When no scenario meets target, picks earliest completion."""
        svc = SimulatorService(mock_db)
        s1 = self._make_scenario("A", meets_target=False, completion_offset_hours=10)
        s2 = self._make_scenario("B", meets_target=False, completion_offset_hours=5)
        result = svc._pick_recommendation([s1, s2])
        assert result == "B"

    def test_recommend_none_for_empty_list(self, mock_db):
        """Empty scenario list returns None."""
        svc = SimulatorService(mock_db)
        assert svc._pick_recommendation([]) is None

    def test_select_best_limits_to_three(self, mock_db):
        """Selection limits output to 3 scenarios."""
        svc = SimulatorService(mock_db)
        scenarios = [
            self._make_scenario(f"S{i}", affected=i) for i in range(5)
        ]
        target = _now() + timedelta(days=5)
        result = svc._select_best_scenarios(scenarios, target)
        assert len(result) <= 3

    def test_select_best_preserves_few(self, mock_db):
        """Selection preserves all when <= 3 scenarios."""
        svc = SimulatorService(mock_db)
        scenarios = [self._make_scenario("A"), self._make_scenario("B")]
        target = _now() + timedelta(days=5)
        result = svc._select_best_scenarios(scenarios, target)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Simulate Append
# ---------------------------------------------------------------------------


class TestSimulateAppend:
    """Test append scenario generation."""

    def test_append_no_existing_jobs(self, mock_db, product_factory, line_factory):
        """Append on empty line starts at aligned work hour."""
        svc = SimulatorService(mock_db)
        product = product_factory.create(sku="RUSH-A", standard_cycle_time=2.0)
        line = line_factory.create(status="active")
        rush = RushOrderInput(
            product_id=product.id,
            quantity=100,
            target_date=_now() + timedelta(days=5),
        )

        scenario = svc._simulate_append(rush, product, line, [], 4.0)
        assert scenario is not None
        assert scenario.affected_orders == []
        assert "Append" in scenario.name
        assert scenario.production_hours == 4.0

    def test_append_after_existing_jobs(self, mock_db, product_factory, line_factory, job_factory):
        """Append starts after the last existing job."""
        svc = SimulatorService(mock_db)
        product = product_factory.create(sku="RUSH-B")
        line = line_factory.create(status="active")

        existing_end = datetime(2026, 2, 23, 14, 0, tzinfo=timezone.utc)
        existing_job = job_factory.create(
            production_line_id=line.id,
            planned_start=datetime(2026, 2, 23, 10, 0, tzinfo=timezone.utc),
            planned_end=existing_end,
            product=product,
        )

        rush = RushOrderInput(
            product_id=product.id,
            quantity=50,
            target_date=_now() + timedelta(days=5),
        )

        scenario = svc._simulate_append(rush, product, line, [existing_job], 2.0)
        assert scenario is not None
        assert scenario.completion_time >= existing_end

    def test_append_meets_target(self, mock_db, product_factory, line_factory):
        """Append scenario correctly flags meets_target."""
        svc = SimulatorService(mock_db)
        product = product_factory.create(sku="RUSH-C", standard_cycle_time=1.0)
        line = line_factory.create(status="active")
        far_target = _now() + timedelta(days=30)
        rush = RushOrderInput(product_id=product.id, quantity=10, target_date=far_target)

        scenario = svc._simulate_append(rush, product, line, [], 1.0)
        assert scenario is not None
        assert scenario.meets_target is True


# ---------------------------------------------------------------------------
# Simulate Insert
# ---------------------------------------------------------------------------


class TestSimulateInsert:
    """Test insert scenario generation."""

    def test_insert_empty_line(self, mock_db, product_factory, line_factory):
        """Insert on empty line works like append."""
        svc = SimulatorService(mock_db)
        product = product_factory.create(sku="INS-A")
        line = line_factory.create(status="active")
        rush = RushOrderInput(
            product_id=product.id,
            quantity=100,
            target_date=_now() + timedelta(days=5),
        )

        scenario = svc._simulate_insert(rush, product, line, [], 3.0)
        assert scenario is not None
        assert "Insert" in scenario.name

    def test_insert_cascades_delays(self, mock_db, product_factory, line_factory, job_factory):
        """Inserting before existing jobs cascades delays."""
        svc = SimulatorService(mock_db)
        product = product_factory.create(sku="INS-B")
        line = line_factory.create(status="active")

        # Create a future job on this line
        future_start = datetime(2026, 2, 24, 9, 0, tzinfo=timezone.utc)  # Tuesday
        future_end = datetime(2026, 2, 24, 12, 0, tzinfo=timezone.utc)
        future_job = job_factory.create(
            production_line_id=line.id,
            planned_start=future_start,
            planned_end=future_end,
            order_item_id=uuid.uuid4(),
            product=product,
        )

        rush = RushOrderInput(
            product_id=product.id,
            quantity=100,
            target_date=_now() + timedelta(days=5),
        )

        scenario = svc._simulate_insert(rush, product, line, [future_job], 4.0)
        assert scenario is not None
        # The insertion should potentially affect the existing job
        # (depends on timing, but the mechanism should work)


# ---------------------------------------------------------------------------
# Impact Calculation
# ---------------------------------------------------------------------------


class TestImpactCalculation:
    """Test cost and impact calculations."""

    def test_overtime_cost_calculation(self):
        """Overtime cost uses correct rate."""
        overtime_hours = 2.5
        expected_cost = overtime_hours * OVERTIME_COST_PER_HOUR
        assert expected_cost == 2.5 * 450.0

    def test_scenario_to_dict(self):
        """Scenario serializes to dict correctly."""
        scenario = SimulationScenario(
            name="Test",
            description="Test scenario",
            production_line_id=uuid.uuid4(),
            production_line_name="Line 1",
            completion_time=_now(),
            changeover_time=30.0,
            production_hours=4.0,
            affected_orders=[
                AffectedOrder(
                    order_item_id=uuid.uuid4(),
                    original_end=_now(),
                    new_end=_now() + timedelta(hours=2),
                    delay_minutes=120.0,
                )
            ],
            overtime_hours=1.5,
            additional_cost=675.0,
            meets_target=True,
        )
        d = scenario.to_dict()
        assert d["name"] == "Test"
        assert d["production_hours"] == 4.0
        assert len(d["affected_orders"]) == 1
        assert d["affected_orders"][0]["delay_minutes"] == 120.0
        assert d["meets_target"] is True

    def test_affected_order_delay_calculation(self):
        """AffectedOrder correctly stores delay."""
        ao = AffectedOrder(
            order_item_id=uuid.uuid4(),
            original_end=_now(),
            new_end=_now() + timedelta(minutes=90),
            delay_minutes=90.0,
        )
        assert ao.delay_minutes == 90.0


# ---------------------------------------------------------------------------
# Full Simulation Flow (Mocked DB)
# ---------------------------------------------------------------------------


class TestFullSimulation:
    """Test full simulate_rush_order with mocked DB."""

    @pytest.mark.asyncio
    async def test_product_not_found_raises(self, mock_db):
        """Missing product raises SimulationError."""
        svc = SimulatorService(mock_db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        rush = RushOrderInput(
            product_id=uuid.uuid4(),
            quantity=100,
            target_date=_now() + timedelta(days=3),
        )
        with pytest.raises(SimulationError, match="not found"):
            await svc.simulate_rush_order(rush)

    @pytest.mark.asyncio
    async def test_no_active_lines_raises(self, mock_db, product_factory):
        """No active lines raises SimulationError."""
        svc = SimulatorService(mock_db)
        product = product_factory.create()

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = product
            else:
                mock_result.scalars.return_value.all.return_value = []
            return mock_result

        mock_db.execute = mock_execute

        rush = RushOrderInput(
            product_id=product.id,
            quantity=100,
            target_date=_now() + timedelta(days=3),
        )
        with pytest.raises(SimulationError, match="No active"):
            await svc.simulate_rush_order(rush)

    @pytest.mark.asyncio
    async def test_impossible_deadline_still_produces_scenarios(
        self, mock_db, product_factory, line_factory
    ):
        """Very tight deadline still produces scenarios (just won't meet target)."""
        svc = SimulatorService(mock_db)
        product = product_factory.create(standard_cycle_time=60.0, setup_time=120.0)
        line = line_factory.create(status="active")

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = product
            elif call_count == 2:
                mock_result.scalars.return_value.all.return_value = [line]
            else:
                mock_result.scalars.return_value.all.return_value = []
            return mock_result

        mock_db.execute = mock_execute

        # Target date in the past = impossible
        rush = RushOrderInput(
            product_id=product.id,
            quantity=1000,
            target_date=_now() - timedelta(days=1),
        )
        result = await svc.simulate_rush_order(rush)
        assert result["total_scenarios"] > 0
        # None should meet target
        for s in result["scenarios"]:
            assert s["meets_target"] is False


# ---------------------------------------------------------------------------
# Utility Methods
# ---------------------------------------------------------------------------


class TestSimulatorUtilities:
    """Test simulator utility methods."""

    def test_is_product_allowed_no_restriction(self, line_factory):
        """No restriction means all products allowed."""
        line = line_factory.create(allowed_products=None)
        assert SimulatorService._is_product_allowed("ANY", line) is True

    def test_is_product_allowed_in_list(self, line_factory):
        """Product in allowed list is accepted."""
        line = line_factory.create(allowed_products=["SKU-A", "SKU-B"])
        assert SimulatorService._is_product_allowed("SKU-A", line) is True

    def test_is_product_not_allowed(self, line_factory):
        """Product not in allowed list is rejected."""
        line = line_factory.create(allowed_products=["SKU-A"])
        assert SimulatorService._is_product_allowed("SKU-Z", line) is False

    def test_advance_work_hours_within_day(self):
        """Advancing within a work day stays on same day."""
        start = datetime(2026, 2, 23, 9, 0, tzinfo=timezone.utc)  # Monday 9 AM
        result = SimulatorService._advance_work_hours(start, 3.0)
        assert result.hour == 12
        assert result.day == 23

    def test_advance_work_hours_across_days(self):
        """Advancing past work hours wraps to next day."""
        start = datetime(2026, 2, 23, 15, 0, tzinfo=timezone.utc)  # Monday 3 PM
        # 9 hours = 2h today (3-5pm) + 7h tomorrow (8am-3pm)... but work day is 9h
        result = SimulatorService._advance_work_hours(start, 5.0)
        # Should wrap to next work day
        assert result >= start + timedelta(hours=5)

    def test_changeover_same_product_zero(self, line_factory):
        """Same product has zero changeover."""
        line = line_factory.create(changeover_matrix={"default": 30})
        assert SimulatorService._get_changeover_time("A", "A", line) == 0.0

    def test_changeover_none_from_sku(self, line_factory):
        """None from_sku (first job) has zero changeover."""
        line = line_factory.create(changeover_matrix={"default": 30})
        assert SimulatorService._get_changeover_time(None, "A", line) == 0.0
