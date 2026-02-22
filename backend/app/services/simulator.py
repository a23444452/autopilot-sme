"""Rush order what-if simulation engine.

Given a rush order (product, quantity, target date), simulates insertion into
the current schedule and produces 2-3 feasible scenarios with impact analysis.
Each scenario includes: completion time, changeover time, affected orders with
delay amounts, additional overtime cost, and a recommendation flag.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.models.production_line import ProductionLine
from app.models.schedule import ScheduledJob
from app.services.production_helpers import (
    DEFAULT_MAX_OVERTIME_HOURS,
    advance_work_hours,
    align_to_work_start,
    calculate_job_overtime,
    fetch_active_lines,
    get_changeover_time,
    is_product_allowed,
)

logger = logging.getLogger(__name__)

# Cost assumptions for overtime calculation
OVERTIME_COST_PER_HOUR = 450.0  # NTD per hour


class SimulationError(Exception):
    """Raised when simulation encounters an unrecoverable error."""


@dataclass
class RushOrderInput:
    """Input parameters for a rush order simulation."""

    product_id: uuid.UUID
    quantity: int
    target_date: datetime
    priority: int = 1  # Rush orders default to highest priority


@dataclass
class AffectedOrder:
    """An existing order impacted by rush order insertion."""

    order_item_id: uuid.UUID
    original_end: datetime
    new_end: datetime
    delay_minutes: float


@dataclass
class SimulationScenario:
    """A single feasible scenario for rush order insertion."""

    name: str
    description: str
    production_line_id: uuid.UUID
    production_line_name: str
    completion_time: datetime
    changeover_time: float  # minutes
    production_hours: float
    affected_orders: list[AffectedOrder] = field(default_factory=list)
    overtime_hours: float = 0.0
    additional_cost: float = 0.0  # NTD
    meets_target: bool = False
    recommendation: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize scenario to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "production_line_id": str(self.production_line_id),
            "production_line_name": self.production_line_name,
            "completion_time": self.completion_time.isoformat(),
            "changeover_time": self.changeover_time,
            "production_hours": round(self.production_hours, 2),
            "affected_orders": [
                {
                    "order_item_id": str(ao.order_item_id),
                    "original_end": ao.original_end.isoformat(),
                    "new_end": ao.new_end.isoformat(),
                    "delay_minutes": round(ao.delay_minutes, 1),
                }
                for ao in self.affected_orders
            ],
            "overtime_hours": round(self.overtime_hours, 2),
            "additional_cost": round(self.additional_cost, 2),
            "meets_target": self.meets_target,
            "recommendation": self.recommendation,
            "warnings": self.warnings,
        }


class SimulatorService:
    """Rush order what-if simulation engine.

    Produces 2-3 feasible scenarios for inserting a rush order into
    the current production schedule with full impact analysis.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def simulate_rush_order(
        self, rush_input: RushOrderInput
    ) -> dict[str, Any]:
        """Run rush order simulation and return feasible scenarios.

        Returns a dict with:
        - scenarios: list of feasible scenario dicts
        - rush_order: input parameters echo
        - recommended_scenario: name of recommended scenario (or None)
        """
        product = await self._fetch_product(rush_input.product_id)
        if product is None:
            raise SimulationError(
                f"Product {rush_input.product_id} not found."
            )

        lines = await self._fetch_active_lines()
        if not lines:
            raise SimulationError("No active production lines available.")

        existing_jobs = await self._fetch_planned_jobs()

        # Calculate rush order production requirements
        cycle_time = product.learned_cycle_time or product.standard_cycle_time
        effective_qty = rush_input.quantity / max(product.yield_rate, 0.01)
        production_hours = (effective_qty * cycle_time) / 60.0 + product.setup_time / 60.0

        # Generate candidate scenarios
        scenarios: list[SimulationScenario] = []

        for line in lines:
            if not is_product_allowed(product.sku, line):
                continue

            # Scenario A: Append to end of line's current schedule
            append_scenario = self._simulate_append(
                rush_input, product, line, existing_jobs, production_hours
            )
            if append_scenario is not None:
                scenarios.append(append_scenario)

            # Scenario B: Insert at earliest gap (preempt lower-priority jobs)
            insert_scenario = self._simulate_insert(
                rush_input, product, line, existing_jobs, production_hours
            )
            if insert_scenario is not None:
                scenarios.append(insert_scenario)

        if not scenarios:
            raise SimulationError(
                "No feasible scenarios found. All production lines are either "
                "at capacity or incompatible with the requested product."
            )

        # Deduplicate and keep best per strategy type, limit to 3
        scenarios = self._select_best_scenarios(scenarios, rush_input.target_date)

        # Pick recommendation
        recommended = self._pick_recommendation(scenarios)

        return {
            "scenarios": [s.to_dict() for s in scenarios],
            "rush_order": {
                "product_id": str(rush_input.product_id),
                "product_sku": product.sku,
                "product_name": product.name,
                "quantity": rush_input.quantity,
                "target_date": rush_input.target_date.isoformat(),
                "estimated_production_hours": round(production_hours, 2),
            },
            "recommended_scenario": recommended,
            "total_scenarios": len(scenarios),
        }

    # ---------------------------------------------------------------
    # Scenario Generation
    # ---------------------------------------------------------------

    def _simulate_append(
        self,
        rush_input: RushOrderInput,
        product: Product,
        line: ProductionLine,
        existing_jobs: list[ScheduledJob],
        production_hours: float,
    ) -> SimulationScenario | None:
        """Simulate appending the rush order after all existing jobs on a line."""
        line_jobs = sorted(
            [j for j in existing_jobs if j.production_line_id == line.id],
            key=lambda j: j.planned_end,
        )

        now = datetime.now(timezone.utc)
        if line_jobs:
            last_job = line_jobs[-1]
            start_after = last_job.planned_end
            last_sku = self._get_job_product_sku(last_job, existing_jobs)
        else:
            start_after = now
            last_sku = None

        # Align to work hours
        start_time = align_to_work_start(start_after)

        # Calculate changeover
        changeover = get_changeover_time(last_sku, product.sku, line)
        job_start = start_time + timedelta(minutes=changeover)
        job_end = advance_work_hours(job_start, production_hours)

        overtime = calculate_job_overtime(job_start, job_end)

        scenario = SimulationScenario(
            name=f"Append to {line.name}",
            description=(
                f"Add rush order after all existing jobs on {line.name}. "
                f"No existing orders are affected."
            ),
            production_line_id=line.id,
            production_line_name=line.name,
            completion_time=job_end,
            changeover_time=changeover,
            production_hours=production_hours,
            affected_orders=[],
            overtime_hours=overtime,
            additional_cost=overtime * OVERTIME_COST_PER_HOUR,
            meets_target=job_end <= rush_input.target_date,
            warnings=[],
        )

        if overtime > DEFAULT_MAX_OVERTIME_HOURS:
            scenario.warnings.append(
                f"Requires {overtime:.1f}h overtime (max {DEFAULT_MAX_OVERTIME_HOURS}h)."
            )

        return scenario

    def _simulate_insert(
        self,
        rush_input: RushOrderInput,
        product: Product,
        line: ProductionLine,
        existing_jobs: list[ScheduledJob],
        production_hours: float,
    ) -> SimulationScenario | None:
        """Simulate inserting rush order at earliest position, pushing back lower-priority jobs."""
        line_jobs = sorted(
            [j for j in existing_jobs if j.production_line_id == line.id],
            key=lambda j: j.planned_start,
        )

        now = datetime.now(timezone.utc)
        insert_time = align_to_work_start(now)

        # Find insertion point: before the first job that hasn't started yet
        insert_idx = 0
        for i, job in enumerate(line_jobs):
            if job.planned_start > now:
                insert_idx = i
                break
        else:
            insert_idx = len(line_jobs)

        # Determine changeover from preceding job
        if insert_idx > 0:
            prev_job = line_jobs[insert_idx - 1]
            insert_time = align_to_work_start(prev_job.planned_end)
            prev_sku = self._get_job_product_sku(prev_job, existing_jobs)
        else:
            prev_sku = None

        changeover_in = get_changeover_time(prev_sku, product.sku, line)
        rush_start = insert_time + timedelta(minutes=changeover_in)
        rush_end = advance_work_hours(rush_start, production_hours)

        # Calculate impact on subsequent jobs
        affected_orders: list[AffectedOrder] = []
        cascade_time = rush_end

        for job in line_jobs[insert_idx:]:
            # Changeover from rush product to this job's product
            job_sku = self._get_job_product_sku(job, existing_jobs)
            changeover_out = get_changeover_time(product.sku, job_sku, line)
            new_start = align_to_work_start(
                cascade_time + timedelta(minutes=changeover_out)
            )

            job_duration_hours = (
                (job.planned_end - job.planned_start).total_seconds() / 3600.0
            )
            new_end = advance_work_hours(new_start, job_duration_hours)

            delay_minutes = max(
                (new_end - job.planned_end).total_seconds() / 60.0, 0.0
            )
            if delay_minutes > 0:
                affected_orders.append(
                    AffectedOrder(
                        order_item_id=job.order_item_id,
                        original_end=job.planned_end,
                        new_end=new_end,
                        delay_minutes=delay_minutes,
                    )
                )

            cascade_time = new_end

        overtime = calculate_job_overtime(rush_start, rush_end)
        # Add overtime from displaced jobs
        for ao in affected_orders:
            overtime += calculate_job_overtime(
                ao.new_end - timedelta(hours=1), ao.new_end
            )

        scenario = SimulationScenario(
            name=f"Insert into {line.name}",
            description=(
                f"Insert rush order at earliest slot on {line.name}, "
                f"pushing back {len(affected_orders)} existing job(s)."
            ),
            production_line_id=line.id,
            production_line_name=line.name,
            completion_time=rush_end,
            changeover_time=changeover_in,
            production_hours=production_hours,
            affected_orders=affected_orders,
            overtime_hours=overtime,
            additional_cost=overtime * OVERTIME_COST_PER_HOUR,
            meets_target=rush_end <= rush_input.target_date,
            warnings=[],
        )

        if affected_orders:
            max_delay = max(ao.delay_minutes for ao in affected_orders)
            scenario.warnings.append(
                f"Maximum delay to existing orders: {max_delay:.0f} minutes."
            )

        if overtime > DEFAULT_MAX_OVERTIME_HOURS:
            scenario.warnings.append(
                f"Requires {overtime:.1f}h overtime (max {DEFAULT_MAX_OVERTIME_HOURS}h)."
            )

        return scenario

    # ---------------------------------------------------------------
    # Scenario Selection & Recommendation
    # ---------------------------------------------------------------

    def _select_best_scenarios(
        self,
        scenarios: list[SimulationScenario],
        target_date: datetime,
    ) -> list[SimulationScenario]:
        """Select up to 3 best scenarios balancing different trade-offs."""
        if len(scenarios) <= 3:
            return scenarios

        # Score each scenario: lower is better
        scored: list[tuple[float, SimulationScenario]] = []
        for s in scenarios:
            score = 0.0
            # Prefer meeting target
            if not s.meets_target:
                late_hours = (s.completion_time - target_date).total_seconds() / 3600.0
                score += late_hours * 10.0
            # Penalty for affected orders
            score += len(s.affected_orders) * 5.0
            # Penalty for total delay
            score += sum(ao.delay_minutes for ao in s.affected_orders) / 60.0
            # Penalty for overtime cost
            score += s.additional_cost / 1000.0
            scored.append((score, s))

        scored.sort(key=lambda x: x[0])

        # Pick best overall, best no-impact (append), and best fast (insert)
        selected: list[SimulationScenario] = []
        seen_names: set[str] = set()

        for _, s in scored:
            if len(selected) >= 3:
                break
            if s.name not in seen_names:
                selected.append(s)
                seen_names.add(s.name)

        return selected

    def _pick_recommendation(
        self, scenarios: list[SimulationScenario]
    ) -> str | None:
        """Pick the recommended scenario based on balanced trade-offs.

        Priority: meets target > fewer affected orders > lower cost.
        """
        if not scenarios:
            return None

        # First preference: meets target with no affected orders
        for s in scenarios:
            if s.meets_target and not s.affected_orders:
                s.recommendation = True
                return s.name

        # Second: meets target with fewest affected orders
        meeting = [s for s in scenarios if s.meets_target]
        if meeting:
            best = min(meeting, key=lambda s: (len(s.affected_orders), s.additional_cost))
            best.recommendation = True
            return best.name

        # Third: earliest completion
        best = min(scenarios, key=lambda s: s.completion_time)
        best.recommendation = True
        return best.name

    # ---------------------------------------------------------------
    # Data Fetching
    # ---------------------------------------------------------------

    async def _fetch_product(self, product_id: uuid.UUID) -> Product | None:
        """Fetch a product by ID."""
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def _fetch_active_lines(self) -> list[ProductionLine]:
        """Fetch all active production lines."""
        return await fetch_active_lines(self.db)

    async def _fetch_planned_jobs(self) -> list[ScheduledJob]:
        """Fetch all currently planned/in-progress jobs with their products."""
        result = await self.db.execute(
            select(ScheduledJob)
            .options(selectinload(ScheduledJob.product))
            .where(ScheduledJob.status.in_(["planned", "in_progress"]))
            .order_by(ScheduledJob.planned_start)
        )
        return list(result.scalars().all())

    # ---------------------------------------------------------------
    # Utility Helpers
    # ---------------------------------------------------------------

    # Backward-compatible static method aliases for external callers
    _advance_work_hours = staticmethod(advance_work_hours)

    @staticmethod
    def _get_job_product_sku(
        job: ScheduledJob, all_jobs: list[ScheduledJob]
    ) -> str | None:
        """Get the product SKU for a scheduled job."""
        if job.product and hasattr(job.product, "sku"):
            return job.product.sku
        return None
