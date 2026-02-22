"""Core scheduling engine implementing a three-phase algorithm.

Phase 1: Rule-based pre-scheduling (sort by due date and priority)
Phase 2: Constraint satisfaction (capacity, changeover times, labor)
Phase 3: AI optimization using historical data via LLM
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.production_line import ProductionLine
from app.models.schedule import ScheduledJob
from app.schemas.schedule import ScheduleRequest, ScheduleResult, ScheduledJobResponse

logger = logging.getLogger(__name__)

# Working hours configuration
DEFAULT_WORK_START_HOUR = 8
DEFAULT_WORK_END_HOUR = 17
DEFAULT_HOURS_PER_DAY = DEFAULT_WORK_END_HOUR - DEFAULT_WORK_START_HOUR
DEFAULT_MAX_OVERTIME_HOURS = 3


class SchedulingError(Exception):
    """Raised when scheduling encounters an unrecoverable error."""


class _OrderTask:
    """Internal representation of a task to be scheduled."""

    __slots__ = (
        "order_item_id",
        "order_id",
        "product_id",
        "product_sku",
        "quantity",
        "due_date",
        "priority",
        "cycle_time",
        "setup_time",
        "yield_rate",
        "estimated_hours",
    )

    def __init__(
        self,
        order_item_id: uuid.UUID,
        order_id: uuid.UUID,
        product_id: uuid.UUID,
        product_sku: str,
        quantity: int,
        due_date: datetime,
        priority: int,
        cycle_time: float,
        setup_time: float,
        yield_rate: float,
    ) -> None:
        self.order_item_id = order_item_id
        self.order_id = order_id
        self.product_id = product_id
        self.product_sku = product_sku
        self.quantity = quantity
        self.due_date = due_date
        self.priority = priority
        self.cycle_time = cycle_time
        self.setup_time = setup_time
        self.yield_rate = yield_rate
        # Effective quantity accounting for yield loss
        effective_qty = quantity / max(yield_rate, 0.01)
        self.estimated_hours = (effective_qty * cycle_time) / 60.0 + setup_time / 60.0


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
        stmt = select(ProductionLine).where(ProductionLine.status == "active")
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
        work_start = self._align_to_work_start(start_time)

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
            overtime = self._calculate_job_overtime(job_start, job_end)
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
            if not self._is_product_allowed(task.product_sku, slot.line):
                continue

            changeover = self._get_changeover_time(
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

    def _is_product_allowed(self, product_sku: str, line: ProductionLine) -> bool:
        """Check if a product is allowed on this production line."""
        if line.allowed_products is None:
            return True
        allowed = line.allowed_products
        if isinstance(allowed, list):
            return product_sku in allowed
        if isinstance(allowed, dict) and "skus" in allowed:
            return product_sku in allowed["skus"]
        return True

    def _get_changeover_time(
        self, from_sku: str | None, to_sku: str, line: ProductionLine
    ) -> float:
        """Get changeover time in minutes between two products on a line."""
        if from_sku is None or from_sku == to_sku:
            return 0.0

        matrix = line.changeover_matrix
        if matrix and isinstance(matrix, dict):
            key = f"{from_sku}->{to_sku}"
            if key in matrix:
                return float(matrix[key])
            # Check reverse or default
            reverse_key = f"{to_sku}->{from_sku}"
            if reverse_key in matrix:
                return float(matrix[reverse_key])
            if "default" in matrix:
                return float(matrix["default"])

        # Default changeover: 30 minutes
        return 30.0

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

    async def _persist_jobs(self, job_dicts: list[dict[str, Any]]) -> list[ScheduledJob]:
        """Create ScheduledJob records in the database."""
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
        total_overtime = sum(self._calculate_job_overtime(j.planned_start, j.planned_end) for j in jobs)

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
            1 for t in tasks if t.cycle_time != t.setup_time  # rough proxy
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

    @staticmethod
    def _align_to_work_start(dt: datetime) -> datetime:
        """Align a datetime to the next available work start time."""
        result = dt.replace(minute=0, second=0, microsecond=0)
        if result.hour < DEFAULT_WORK_START_HOUR:
            result = result.replace(hour=DEFAULT_WORK_START_HOUR)
        elif result.hour >= DEFAULT_WORK_END_HOUR:
            result = result + timedelta(days=1)
            result = result.replace(hour=DEFAULT_WORK_START_HOUR)
        # Skip weekends
        while result.weekday() >= 5:
            result += timedelta(days=1)
        return result

    @staticmethod
    def _calculate_job_overtime(start: datetime, end: datetime) -> float:
        """Calculate overtime hours for a job spanning start to end."""
        overtime = 0.0
        current = start
        while current < end:
            day_end_regular = current.replace(
                hour=DEFAULT_WORK_END_HOUR, minute=0, second=0, microsecond=0
            )
            if current >= day_end_regular:
                # All remaining time today is overtime
                next_day = (current + timedelta(days=1)).replace(
                    hour=DEFAULT_WORK_START_HOUR, minute=0, second=0, microsecond=0
                )
                ot_end = min(end, next_day)
                overtime += (ot_end - current).total_seconds() / 3600.0
                current = next_day
            else:
                # Move to end of regular hours or job end
                current = min(end, day_end_regular)
        return max(overtime, 0.0)

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
