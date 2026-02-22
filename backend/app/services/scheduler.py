"""Core scheduling engine implementing a three-phase algorithm.

Phase 1: Rule-based pre-scheduling (sort by due date and priority)
Phase 2: Constraint satisfaction (capacity, changeover times, labor)
Phase 3: AI optimization using historical data via LLM
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.production_line import ProductionLine
from app.models.schedule import ScheduledJob
from app.schemas.schedule import ScheduleRequest, ScheduleResult, ScheduledJobResponse
from app.services.production_helpers import (
    DEFAULT_HOURS_PER_DAY,
    DEFAULT_MAX_OVERTIME_HOURS,
    DEFAULT_WORK_END_HOUR,
    DEFAULT_WORK_START_HOUR,
    align_to_work_start,
    calculate_job_overtime,
    fetch_active_lines,
    get_changeover_time,
    is_product_allowed,
)

logger = logging.getLogger(__name__)


class SchedulingError(Exception):
    """Raised when scheduling encounters an unrecoverable error."""


@dataclass
class _OrderTask:
    """Internal representation of a task to be scheduled."""

    order_item_id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID
    product_sku: str
    quantity: int
    due_date: datetime
    priority: int
    cycle_time: float
    setup_time: float
    yield_rate: float
    has_learned_cycle_time: bool = False
    estimated_hours: float = 0.0

    def __post_init__(self) -> None:
        effective_qty = self.quantity / max(self.yield_rate, 0.01)
        self.estimated_hours = (effective_qty * self.cycle_time) / 60.0 + self.setup_time / 60.0


class _LineSlot:
    """Tracks current state of a production line during scheduling."""

    __slots__ = ("line", "current_time", "last_product_sku", "total_busy_hours", "overtime_hours")

    def __init__(self, line: ProductionLine, start_time: datetime) -> None:
        self.line = line
        self.current_time = start_time
        self.last_product_sku: str | None = None
        self.total_busy_hours: float = 0.0
        self.overtime_hours: float = 0.0


class SchedulerService:
    """Three-phase production scheduling engine."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_schedule(self, request: ScheduleRequest) -> ScheduleResult:
        """Generate an optimized production schedule using the three-phase algorithm.

        Phase 1: Rule-based sort by due date and priority
        Phase 2: Constraint satisfaction for capacity, changeover, labor
        Phase 3: AI optimization placeholder (returns Phase 2 result with metadata)
        """
        # Fetch data
        orders = await self._fetch_orders(request.order_ids)
        lines = await self._fetch_active_lines()
        warnings: list[str] = []

        if not lines:
            return ScheduleResult(
                jobs=[],
                total_jobs=0,
                warnings=["No active production lines configured. Please set up lines before scheduling."],
            )

        if not orders:
            return ScheduleResult(
                jobs=[],
                total_jobs=0,
                warnings=["No pending orders found to schedule."],
            )

        # Build task list from order items
        tasks = self._build_tasks(orders)
        if not tasks:
            return ScheduleResult(
                jobs=[],
                total_jobs=0,
                warnings=["No schedulable order items found."],
            )

        # Phase 1: Rule-based sort
        sorted_tasks = self._phase1_rule_based_sort(tasks)

        # Phase 2: Constraint satisfaction
        now = datetime.now(timezone.utc)
        horizon_end = now + timedelta(days=request.horizon_days)
        scheduled_jobs, phase2_warnings = self._phase2_constraint_satisfaction(
            sorted_tasks, lines, now, horizon_end, request.strategy
        )
        warnings.extend(phase2_warnings)

        # Phase 3: AI optimization (placeholder — enhances with metadata)
        optimized_jobs, phase3_meta = await self._phase3_ai_optimize(
            scheduled_jobs, sorted_tasks, lines
        )

        # Persist to database
        persisted = await self._persist_jobs(optimized_jobs)

        # Calculate metrics
        metrics = self._calculate_metrics(persisted, lines, now, horizon_end, tasks)
        confidence = self._calculate_confidence(persisted, tasks, lines)

        return ScheduleResult(
            jobs=[self._job_to_response(j) for j in persisted],
            total_jobs=len(persisted),
            total_changeover_minutes=sum(j.changeover_time for j in persisted),
            utilization_pct=metrics["utilization_pct"],
            warnings=warnings,
            metadata={
                "on_time_delivery_rate": metrics["on_time_delivery_rate"],
                "overtime_hours": metrics["overtime_hours"],
                "confidence_score": confidence,
                "strategy": request.strategy,
                "horizon_days": request.horizon_days,
                "phase3_applied": phase3_meta.get("applied", False),
                **phase3_meta,
            },
        )

    # ---------------------------------------------------------------
    # Data Fetching
    # ---------------------------------------------------------------

    async def _fetch_orders(self, order_ids: list[uuid.UUID]) -> list[Order]:
        """Fetch pending orders with their items and products."""
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.status.in_(["pending", "confirmed"]))
        )
        if order_ids:
            stmt = stmt.where(Order.id.in_(order_ids))
        stmt = stmt.order_by(Order.due_date)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _fetch_active_lines(self) -> list[ProductionLine]:
        """Fetch all active production lines."""
        return await fetch_active_lines(self.db)

    # ---------------------------------------------------------------
    # Phase 1: Rule-based Sort
    # ---------------------------------------------------------------

    def _build_tasks(self, orders: list[Order]) -> list[_OrderTask]:
        """Convert orders/items into schedulable tasks."""
        tasks: list[_OrderTask] = []
        for order in orders:
            for item in order.items:
                product: Product = item.product
                cycle_time = product.learned_cycle_time or product.standard_cycle_time
                tasks.append(
                    _OrderTask(
                        order_item_id=item.id,
                        order_id=order.id,
                        product_id=product.id,
                        product_sku=product.sku,
                        quantity=item.quantity,
                        due_date=order.due_date,
                        priority=order.priority,
                        cycle_time=cycle_time,
                        setup_time=product.setup_time,
                        yield_rate=product.yield_rate,
                        has_learned_cycle_time=product.learned_cycle_time is not None,
                    )
                )
        return tasks

    def _phase1_rule_based_sort(self, tasks: list[_OrderTask]) -> list[_OrderTask]:
        """Sort tasks by priority (lower = higher priority), then by due date (earliest first)."""
        return sorted(tasks, key=lambda t: (t.priority, t.due_date))

    # ---------------------------------------------------------------
    # Phase 2: Constraint Satisfaction
    # ---------------------------------------------------------------

    def _phase2_constraint_satisfaction(
        self,
        tasks: list[_OrderTask],
        lines: list[ProductionLine],
        start_time: datetime,
        horizon_end: datetime,
        strategy: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Assign tasks to lines respecting capacity, changeover, and labor constraints.

        Returns a list of job dicts and any warnings.
        """
        warnings: list[str] = []

        # Align start_time to next work hour
        work_start = align_to_work_start(start_time)

        # Initialize line slots
        slots = [_LineSlot(line, work_start) for line in lines]

        jobs: list[dict[str, Any]] = []
        unscheduled: list[_OrderTask] = []

        for task in tasks:
            best_slot, changeover = self._find_best_slot(task, slots, strategy, horizon_end)

            if best_slot is None:
                unscheduled.append(task)
                continue

            # Calculate times
            changeover_minutes = changeover
            job_start = best_slot.current_time + timedelta(minutes=changeover_minutes)
            production_hours = task.estimated_hours
            job_end = job_start + timedelta(hours=production_hours)

            # Check if job exceeds horizon
            if job_end > horizon_end:
                warnings.append(
                    f"Order item {task.order_item_id} extends beyond planning horizon."
                )

            # Track overtime
            overtime = calculate_job_overtime(job_start, job_end)
            if overtime > DEFAULT_MAX_OVERTIME_HOURS:
                warnings.append(
                    f"Order item {task.order_item_id} requires {overtime:.1f}h overtime "
                    f"(max {DEFAULT_MAX_OVERTIME_HOURS}h)."
                )

            # Check on-time delivery
            if job_end > task.due_date:
                warnings.append(
                    f"Order item {task.order_item_id} is projected to finish after due date."
                )

            jobs.append({
                "order_item_id": task.order_item_id,
                "production_line_id": best_slot.line.id,
                "product_id": task.product_id,
                "planned_start": job_start,
                "planned_end": job_end,
                "quantity": task.quantity,
                "changeover_time": changeover_minutes,
                "status": "planned",
                "notes": None,
            })

            # Update slot state
            best_slot.current_time = job_end
            best_slot.last_product_sku = task.product_sku
            best_slot.total_busy_hours += production_hours + changeover_minutes / 60.0
            best_slot.overtime_hours += overtime

        if unscheduled:
            warnings.append(
                f"{len(unscheduled)} order item(s) could not be scheduled within "
                f"the planning horizon due to capacity constraints."
            )

        return jobs, warnings

    def _find_best_slot(
        self,
        task: _OrderTask,
        slots: list[_LineSlot],
        strategy: str,
        horizon_end: datetime,
    ) -> tuple[_LineSlot | None, float]:
        """Find the best production line slot for a task.

        Returns (slot, changeover_minutes) or (None, 0) if no slot fits.
        """
        candidates: list[tuple[_LineSlot, float, float]] = []

        for slot in slots:
            # Check if product is allowed on this line
            if not is_product_allowed(task.product_sku, slot.line):
                continue

            changeover = get_changeover_time(
                slot.last_product_sku, task.product_sku, slot.line
            )

            # Estimate finish time
            job_start = slot.current_time + timedelta(minutes=changeover)
            job_end = job_start + timedelta(hours=task.estimated_hours)

            if job_end > horizon_end + timedelta(hours=DEFAULT_MAX_OVERTIME_HOURS):
                continue

            # Score: lower is better
            score = self._score_assignment(task, slot, changeover, job_end, strategy)
            candidates.append((slot, changeover, score))

        if not candidates:
            return None, 0.0

        # Pick best scoring candidate
        candidates.sort(key=lambda c: c[2])
        best = candidates[0]
        return best[0], best[1]

    def _score_assignment(
        self,
        task: _OrderTask,
        slot: _LineSlot,
        changeover: float,
        job_end: datetime,
        strategy: str,
    ) -> float:
        """Score a line assignment. Lower is better."""
        # Base: earliest finish time
        finish_delta = (job_end - datetime(2000, 1, 1, tzinfo=timezone.utc)).total_seconds()
        score = finish_delta / 3600.0  # Normalize to hours

        # Penalty for changeover
        score += changeover / 10.0

        # Penalty for late delivery
        if job_end > task.due_date:
            late_hours = (job_end - task.due_date).total_seconds() / 3600.0
            score += late_hours * 100.0  # Heavy penalty

        # Strategy adjustments
        if strategy == "rush":
            # Minimize finish time even more
            score -= changeover / 20.0  # Less penalty for changeover
        elif strategy == "efficiency":
            # Minimize changeover more
            score += changeover * 2.0

        # Prefer lines with less load (balance)
        score += slot.total_busy_hours * 0.5

        return score

    # ---------------------------------------------------------------
    # Phase 3: AI Optimization (Placeholder)
    # ---------------------------------------------------------------

    async def _phase3_ai_optimize(
        self,
        jobs: list[dict[str, Any]],
        tasks: list[_OrderTask],
        lines: list[ProductionLine],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Phase 3: AI-based optimization using historical data via LLM.

        Currently a placeholder that returns the constraint-satisfied schedule
        unchanged. When the LLM router is available, this will:
        - Analyze historical production data for pattern recognition
        - Suggest reordering for better line utilization
        - Predict potential bottlenecks based on past performance
        """
        meta: dict[str, Any] = {
            "applied": False,
            "reason": "LLM router not yet integrated",
        }

        # TODO: Integrate with LLMRouter for AI-based suggestions
        # try:
        #     from app.services.llm_router import LLMRouter
        #     router = LLMRouter()
        #     suggestions = await router.call(prompt, system, task_type="scheduling")
        #     jobs = self._apply_ai_suggestions(jobs, suggestions)
        #     meta["applied"] = True
        # except Exception as e:
        #     meta["reason"] = str(e)

        return jobs, meta

    # ---------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------

    async def _supersede_planned_jobs(self, order_item_ids: list[uuid.UUID]) -> int:
        """Mark existing 'planned' jobs as 'superseded' for the given order items.

        This prevents duplicate scheduled jobs from accumulating when
        generate_schedule is called multiple times.  Only jobs with status
        'planned' are affected; 'in_progress' or 'completed' jobs are
        left untouched.

        Returns the number of superseded jobs.
        """
        if not order_item_ids:
            return 0

        result = await self.db.execute(
            update(ScheduledJob)
            .where(
                ScheduledJob.order_item_id.in_(order_item_ids),
                ScheduledJob.status == "planned",
            )
            .values(status="superseded")
            .returning(ScheduledJob.id)
        )
        superseded_ids = list(result.scalars().all())
        if superseded_ids:
            logger.info(
                "Superseded %d planned job(s) before re-scheduling",
                len(superseded_ids),
            )
        return len(superseded_ids)

    async def _persist_jobs(self, job_dicts: list[dict[str, Any]]) -> list[ScheduledJob]:
        """Supersede existing planned jobs, then create new ScheduledJob records."""
        # Collect order item IDs that are about to be re-scheduled
        order_item_ids = [jd["order_item_id"] for jd in job_dicts]
        await self._supersede_planned_jobs(order_item_ids)

        jobs: list[ScheduledJob] = []
        for jd in job_dicts:
            job = ScheduledJob(
                order_item_id=jd["order_item_id"],
                production_line_id=jd["production_line_id"],
                product_id=jd["product_id"],
                planned_start=jd["planned_start"],
                planned_end=jd["planned_end"],
                quantity=jd["quantity"],
                changeover_time=jd["changeover_time"],
                status=jd["status"],
                notes=jd["notes"],
            )
            self.db.add(job)
            jobs.append(job)

        await self.db.flush()
        return jobs

    # ---------------------------------------------------------------
    # Metrics Calculation
    # ---------------------------------------------------------------

    def _calculate_metrics(
        self,
        jobs: list[ScheduledJob],
        lines: list[ProductionLine],
        start_time: datetime,
        horizon_end: datetime,
        tasks: list[_OrderTask],
    ) -> dict[str, float]:
        """Calculate schedule quality metrics."""
        if not jobs:
            return {
                "on_time_delivery_rate": 0.0,
                "utilization_pct": 0.0,
                "overtime_hours": 0.0,
            }

        # On-time delivery rate
        task_map = {t.order_item_id: t for t in tasks}
        on_time = sum(
            1
            for j in jobs
            if j.order_item_id in task_map
            and j.planned_end <= task_map[j.order_item_id].due_date
        )
        on_time_rate = (on_time / len(jobs) * 100.0) if jobs else 0.0

        # Line utilization
        horizon_hours = (horizon_end - start_time).total_seconds() / 3600.0
        total_available_hours = horizon_hours * len(lines)
        total_busy_hours = sum(
            (j.planned_end - j.planned_start).total_seconds() / 3600.0 for j in jobs
        )
        utilization = (total_busy_hours / total_available_hours * 100.0) if total_available_hours > 0 else 0.0

        # Overtime hours
        total_overtime = sum(calculate_job_overtime(j.planned_start, j.planned_end) for j in jobs)

        return {
            "on_time_delivery_rate": round(on_time_rate, 1),
            "utilization_pct": round(min(utilization, 100.0), 1),
            "overtime_hours": round(total_overtime, 1),
        }

    def _calculate_confidence(
        self,
        jobs: list[ScheduledJob],
        tasks: list[_OrderTask],
        lines: list[ProductionLine],
    ) -> float:
        """Calculate schedule confidence score (0-100).

        Factors:
        - Data completeness (products have learned cycle times)
        - Schedule feasibility (jobs finish within horizon)
        - Capacity headroom (lines not overloaded)
        """
        if not jobs or not tasks:
            return 0.0

        scores: list[float] = []

        # Factor 1: Data quality — do products have learned cycle times?
        tasks_with_learned = sum(
            1 for t in tasks if t.has_learned_cycle_time
        )
        data_score = min(tasks_with_learned / max(len(tasks), 1) * 100.0, 100.0)
        scores.append(data_score)

        # Factor 2: On-time ratio
        task_map = {t.order_item_id: t for t in tasks}
        on_time = sum(
            1
            for j in jobs
            if j.order_item_id in task_map
            and j.planned_end <= task_map[j.order_item_id].due_date
        )
        on_time_score = (on_time / len(jobs) * 100.0) if jobs else 0.0
        scores.append(on_time_score)

        # Factor 3: Capacity headroom (penalize if many warnings)
        coverage = len(jobs) / max(len(tasks), 1)
        coverage_score = coverage * 100.0
        scores.append(coverage_score)

        # Weighted average
        weights = [0.2, 0.5, 0.3]
        confidence = sum(s * w for s, w in zip(scores, weights))
        return round(min(max(confidence, 0.0), 100.0), 1)

    # ---------------------------------------------------------------
    # Utility Helpers
    # ---------------------------------------------------------------

    # Backward-compatible static method aliases for external callers
    _align_to_work_start = staticmethod(align_to_work_start)
    _calculate_job_overtime = staticmethod(calculate_job_overtime)

    @staticmethod
    def _job_to_response(job: ScheduledJob) -> ScheduledJobResponse:
        """Convert a ScheduledJob model to a response schema."""
        return ScheduledJobResponse(
            id=job.id,
            order_item_id=job.order_item_id,
            production_line_id=job.production_line_id,
            product_id=job.product_id,
            planned_start=job.planned_start,
            planned_end=job.planned_end,
            quantity=job.quantity,
            changeover_time=job.changeover_time,
            status=job.status,
            notes=job.notes,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
