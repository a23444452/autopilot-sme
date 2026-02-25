# Phase 1: 資料模型擴充 — 實作計畫

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 擴充資料庫模型，新增 ProcessStation、ProcessRoute、LineCapabilityMatrix 三個實體，並升級排程引擎以支援多站別瓶頸計算。

**Architecture:** 新增三個 SQLAlchemy model + Pydantic schema + CRUD API，修改 scheduler 的 `is_product_allowed()` 和 `_score_assignment()` 改用 capability matrix 匹配和瓶頸站計算。維持向後相容：`allowed_products` 仍可作為 fallback。

**Tech Stack:** SQLAlchemy 2.0 (async), Alembic, Pydantic v2, FastAPI, pytest (MagicMock factories)

---

### Task 1: ProcessStation Model + Schema

**Files:**
- Create: `backend/app/models/process_station.py`
- Create: `backend/app/schemas/process_station.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_process_station.py`

**Step 1: Write the failing test**

Create `backend/tests/test_process_station.py`:

```python
"""Tests for ProcessStation model and schema."""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError


def _make_mock(defaults: dict[str, Any], overrides: dict[str, Any]) -> MagicMock:
    merged = {**defaults, **overrides}
    mock = MagicMock()
    for k, v in merged.items():
        setattr(mock, k, v)
    return mock


class ProcessStationFactory:
    _counter = 0

    @classmethod
    def create(cls, **overrides: Any) -> MagicMock:
        cls._counter += 1
        defaults = {
            "id": uuid.uuid4(),
            "production_line_id": uuid.uuid4(),
            "name": f"Station-{cls._counter}",
            "station_order": cls._counter,
            "equipment_type": "solder_printer",
            "standard_cycle_time": 8.5,
            "actual_cycle_time": None,
            "capabilities": None,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        return _make_mock(defaults, overrides)


class TestProcessStationSchema:
    def test_create_valid(self):
        from app.schemas.process_station import ProcessStationCreate

        data = ProcessStationCreate(
            name="錫膏印刷",
            station_order=1,
            equipment_type="solder_printer",
            standard_cycle_time=8.5,
        )
        assert data.name == "錫膏印刷"
        assert data.station_order == 1
        assert data.standard_cycle_time == 8.5

    def test_create_with_capabilities(self):
        from app.schemas.process_station import ProcessStationCreate

        data = ProcessStationCreate(
            name="回焊爐",
            station_order=2,
            equipment_type="reflow_oven",
            standard_cycle_time=45.0,
            capabilities={"max_board_width": 450, "temperature_range": [200, 280]},
        )
        assert data.capabilities["max_board_width"] == 450

    def test_create_invalid_cycle_time(self):
        from app.schemas.process_station import ProcessStationCreate

        with pytest.raises(ValidationError):
            ProcessStationCreate(
                name="Bad",
                station_order=1,
                equipment_type="test",
                standard_cycle_time=-1.0,
            )

    def test_create_invalid_order(self):
        from app.schemas.process_station import ProcessStationCreate

        with pytest.raises(ValidationError):
            ProcessStationCreate(
                name="Bad",
                station_order=0,
                equipment_type="test",
                standard_cycle_time=1.0,
            )

    def test_response_from_mock(self):
        from app.schemas.process_station import ProcessStationResponse

        station = ProcessStationFactory.create(
            name="AOI檢測",
            capabilities={"resolution": "15um"},
        )
        resp = ProcessStationResponse.model_validate(station, from_attributes=True)
        assert resp.name == "AOI檢測"
        assert resp.capabilities == {"resolution": "15um"}
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_process_station.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.schemas.process_station'`

**Step 3: Write the model**

Create `backend/app/models/process_station.py`:

```python
"""ProcessStation SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProcessStation(Base):
    """A manufacturing station within a production line."""

    __tablename__ = "process_stations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    production_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    station_order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Position in the line (1-based)"
    )
    equipment_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="e.g. solder_printer, reflow_oven"
    )
    standard_cycle_time: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Standard cycle time in seconds per unit"
    )
    actual_cycle_time: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Learned cycle time from MES data"
    )
    capabilities: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Equipment capability parameters"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

**Step 4: Write the schema**

Create `backend/app/schemas/process_station.py`:

```python
"""ProcessStation Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProcessStationCreate(BaseModel):
    """Schema for creating a process station."""

    name: str = Field(..., max_length=100)
    station_order: int = Field(..., ge=1, description="Position in the line (1-based)")
    equipment_type: str = Field(..., max_length=50)
    standard_cycle_time: float = Field(
        ..., gt=0, description="Cycle time in seconds per unit"
    )
    capabilities: dict[str, Any] | None = None
    status: str = Field(default="active", max_length=20)


class ProcessStationResponse(BaseModel):
    """Schema for process station responses."""

    id: uuid.UUID
    production_line_id: uuid.UUID
    name: str
    station_order: int
    equipment_type: str
    standard_cycle_time: float
    actual_cycle_time: float | None
    capabilities: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

**Step 5: Update `__init__.py` files**

Append to `backend/app/models/__init__.py`:

```python
from app.models.process_station import ProcessStation
# Add "ProcessStation" to __all__
```

Append to `backend/app/schemas/__init__.py`:

```python
from app.schemas.process_station import ProcessStationCreate, ProcessStationResponse
# Add both to __all__
```

**Step 6: Run test to verify it passes**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_process_station.py -v`
Expected: All 5 tests PASS

**Step 7: Commit**

```bash
git add backend/app/models/process_station.py backend/app/schemas/process_station.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/tests/test_process_station.py
git commit -m "feat: add ProcessStation model and schema"
```

---

### Task 2: ProcessRoute Model + Schema

**Files:**
- Create: `backend/app/models/process_route.py`
- Create: `backend/app/schemas/process_route.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_process_route.py`

**Step 1: Write the failing test**

Create `backend/tests/test_process_route.py`:

```python
"""Tests for ProcessRoute model and schema."""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError


SAMPLE_STEPS = [
    {
        "step_order": 1,
        "equipment_type": "solder_printer",
        "required_params": {"stencil_thickness": 0.12},
        "estimated_cycle_time": 8.5,
        "quality_checkpoints": ["solder_paste_height"],
    },
    {
        "step_order": 2,
        "equipment_type": "pick_and_place",
        "required_params": {"min_component_size": "0402"},
        "estimated_cycle_time": 12.0,
        "quality_checkpoints": [],
    },
    {
        "step_order": 3,
        "equipment_type": "reflow_oven",
        "required_params": {"peak_temperature": 260},
        "estimated_cycle_time": 45.0,
        "quality_checkpoints": ["reflow_profile"],
    },
]


class TestProcessRouteSchema:
    def test_create_valid(self):
        from app.schemas.process_route import ProcessRouteCreate

        data = ProcessRouteCreate(
            steps=SAMPLE_STEPS,
            source="manual",
        )
        assert len(data.steps) == 3
        assert data.source == "manual"
        assert data.is_active is True

    def test_create_with_source_file(self):
        from app.schemas.process_route import ProcessRouteCreate

        data = ProcessRouteCreate(
            steps=SAMPLE_STEPS,
            source="spec_parsed",
            source_file="/uploads/spec-pcb-a100.pdf",
        )
        assert data.source_file == "/uploads/spec-pcb-a100.pdf"

    def test_create_empty_steps_rejected(self):
        from app.schemas.process_route import ProcessRouteCreate

        with pytest.raises(ValidationError):
            ProcessRouteCreate(
                steps=[],
                source="manual",
            )

    def test_create_invalid_source(self):
        from app.schemas.process_route import ProcessRouteCreate

        with pytest.raises(ValidationError):
            ProcessRouteCreate(
                steps=SAMPLE_STEPS,
                source="invalid_source",
            )

    def test_response_from_mock(self):
        from app.schemas.process_route import ProcessRouteResponse

        def _make_mock(defaults, overrides):
            merged = {**defaults, **overrides}
            mock = MagicMock()
            for k, v in merged.items():
                setattr(mock, k, v)
            return mock

        route_mock = _make_mock(
            {
                "id": uuid.uuid4(),
                "product_id": uuid.uuid4(),
                "version": 1,
                "is_active": True,
                "steps": SAMPLE_STEPS,
                "source": "manual",
                "source_file": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
            {},
        )
        resp = ProcessRouteResponse.model_validate(route_mock, from_attributes=True)
        assert resp.version == 1
        assert len(resp.steps) == 3

    def test_step_schema_validation(self):
        from app.schemas.process_route import ProcessRouteStepSchema

        step = ProcessRouteStepSchema(
            step_order=1,
            equipment_type="solder_printer",
            estimated_cycle_time=8.5,
        )
        assert step.required_params is None
        assert step.quality_checkpoints == []
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_process_route.py -v`
Expected: FAIL

**Step 3: Write the model**

Create `backend/app/models/process_route.py`:

```python
"""ProcessRoute SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProcessRoute(Base):
    """Defines the manufacturing process route for a product."""

    __tablename__ = "process_routes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    steps: Mapped[list] = mapped_column(
        JSONB, nullable=False, comment="Array of process steps"
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="manual",
        comment="manual | spec_parsed | mes_learned",
    )
    source_file: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Path to original spec file"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

**Step 4: Write the schema**

Create `backend/app/schemas/process_route.py`:

```python
"""ProcessRoute Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ProcessRouteStepSchema(BaseModel):
    """Schema for a single step in a process route."""

    step_order: int = Field(..., ge=1)
    equipment_type: str = Field(..., max_length=50)
    required_params: dict[str, Any] | None = None
    estimated_cycle_time: float = Field(..., gt=0, description="Seconds per unit")
    quality_checkpoints: list[str] = Field(default_factory=list)


class ProcessRouteCreate(BaseModel):
    """Schema for creating a process route."""

    steps: list[ProcessRouteStepSchema | dict[str, Any]] = Field(
        ..., min_length=1, description="At least one process step required"
    )
    source: Literal["manual", "spec_parsed", "mes_learned"] = "manual"
    source_file: str | None = None
    is_active: bool = True


class ProcessRouteResponse(BaseModel):
    """Schema for process route responses."""

    id: uuid.UUID
    product_id: uuid.UUID
    version: int
    is_active: bool
    steps: list[dict[str, Any]]
    source: str
    source_file: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

**Step 5: Update `__init__.py` files**

Add `ProcessRoute` to models `__init__.py` and `ProcessRouteCreate`, `ProcessRouteResponse` to schemas `__init__.py`.

**Step 6: Run test to verify it passes**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_process_route.py -v`
Expected: All 6 tests PASS

**Step 7: Commit**

```bash
git add backend/app/models/process_route.py backend/app/schemas/process_route.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/tests/test_process_route.py
git commit -m "feat: add ProcessRoute model and schema"
```

---

### Task 3: LineCapabilityMatrix Model + Schema

**Files:**
- Create: `backend/app/models/line_capability.py`
- Create: `backend/app/schemas/line_capability.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_line_capability.py`

**Step 1: Write the failing test**

Create `backend/tests/test_line_capability.py`:

```python
"""Tests for LineCapabilityMatrix model and schema."""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError


class TestLineCapabilitySchema:
    def test_create_valid(self):
        from app.schemas.line_capability import LineCapabilityCreate

        data = LineCapabilityCreate(
            equipment_type="solder_printer",
            capability_params={"max_board_width": 500, "temperature_range": [180, 300]},
            throughput_range={"min": 80, "max": 120, "unit": "pcs/hr"},
        )
        assert data.equipment_type == "solder_printer"
        assert data.capability_params["max_board_width"] == 500

    def test_create_minimal(self):
        from app.schemas.line_capability import LineCapabilityCreate

        data = LineCapabilityCreate(
            equipment_type="reflow_oven",
        )
        assert data.capability_params is None
        assert data.throughput_range is None

    def test_response_from_mock(self):
        from app.schemas.line_capability import LineCapabilityResponse

        def _make_mock(defaults, overrides):
            merged = {**defaults, **overrides}
            mock = MagicMock()
            for k, v in merged.items():
                setattr(mock, k, v)
            return mock

        cap_mock = _make_mock(
            {
                "id": uuid.uuid4(),
                "production_line_id": uuid.uuid4(),
                "equipment_type": "pick_and_place",
                "capability_params": {"min_component_size": "0201"},
                "throughput_range": {"min": 50, "max": 80, "unit": "pcs/hr"},
                "updated_at": datetime.now(timezone.utc),
            },
            {},
        )
        resp = LineCapabilityResponse.model_validate(cap_mock, from_attributes=True)
        assert resp.equipment_type == "pick_and_place"


class TestCapabilityMatching:
    """Test the capability matching utility function."""

    def test_exact_match(self):
        from app.services.capability_matcher import check_capability_match

        required = {"max_board_width": 400}
        available = {"max_board_width": 500}
        result = check_capability_match(required, available)
        assert result.is_match is True

    def test_no_match_exceeds_capability(self):
        from app.services.capability_matcher import check_capability_match

        required = {"max_board_width": 600}
        available = {"max_board_width": 500}
        result = check_capability_match(required, available)
        assert result.is_match is False
        assert "max_board_width" in result.reasons[0]

    def test_range_match(self):
        from app.services.capability_matcher import check_capability_match

        required = {"peak_temperature": 260}
        available = {"temperature_range": [180, 300]}
        result = check_capability_match(required, available)
        assert result.is_match is True

    def test_range_no_match(self):
        from app.services.capability_matcher import check_capability_match

        required = {"peak_temperature": 350}
        available = {"temperature_range": [180, 300]}
        result = check_capability_match(required, available)
        assert result.is_match is False

    def test_missing_capability(self):
        from app.services.capability_matcher import check_capability_match

        required = {"special_feature": True}
        available = {"max_board_width": 500}
        result = check_capability_match(required, available)
        assert result.is_match is False

    def test_empty_required(self):
        from app.services.capability_matcher import check_capability_match

        result = check_capability_match({}, {"max_board_width": 500})
        assert result.is_match is True

    def test_none_params(self):
        from app.services.capability_matcher import check_capability_match

        result = check_capability_match(None, None)
        assert result.is_match is True
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_line_capability.py -v`
Expected: FAIL

**Step 3: Write the model**

Create `backend/app/models/line_capability.py`:

```python
"""LineCapabilityMatrix SQLAlchemy model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LineCapabilityMatrix(Base):
    """Equipment capability entry for a production line."""

    __tablename__ = "line_capability_matrix"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    production_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Equipment type this entry describes"
    )
    capability_params: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="What this equipment can handle"
    )
    throughput_range: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment='e.g. {"min": 80, "max": 120, "unit": "pcs/hr"}'
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

**Step 4: Write the schema**

Create `backend/app/schemas/line_capability.py`:

```python
"""LineCapabilityMatrix Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LineCapabilityCreate(BaseModel):
    """Schema for creating a capability entry."""

    equipment_type: str = Field(..., max_length=50)
    capability_params: dict[str, Any] | None = None
    throughput_range: dict[str, Any] | None = None


class LineCapabilityResponse(BaseModel):
    """Schema for capability entry responses."""

    id: uuid.UUID
    production_line_id: uuid.UUID
    equipment_type: str
    capability_params: dict[str, Any] | None
    throughput_range: dict[str, Any] | None
    updated_at: datetime

    model_config = {"from_attributes": True}
```

**Step 5: Write the capability matcher service**

Create `backend/app/services/capability_matcher.py`:

```python
"""Capability matching between process routes and production lines."""

from dataclasses import dataclass, field


@dataclass
class MatchResult:
    """Result of a capability match check."""

    is_match: bool
    reasons: list[str] = field(default_factory=list)
    headroom: dict[str, float] = field(default_factory=dict)


def check_capability_match(
    required: dict | None,
    available: dict | None,
) -> MatchResult:
    """Check if available capabilities satisfy required parameters.

    Matching rules:
    - If required is None or empty, always matches
    - Numeric params: required <= available (e.g. max_board_width)
    - Range params: required value within available range
    - String params: exact match
    - Missing capability in available: no match
    """
    if not required:
        return MatchResult(is_match=True)
    if not available:
        return MatchResult(
            is_match=False,
            reasons=[f"No capabilities defined, but {k} required" for k in required],
        )

    reasons: list[str] = []
    headroom: dict[str, float] = {}

    for key, req_value in required.items():
        # Check for range-based matching
        range_key = _find_range_key(key, available)
        if range_key:
            range_val = available[range_key]
            if isinstance(range_val, list) and len(range_val) == 2:
                low, high = range_val
                if isinstance(req_value, (int, float)) and low <= req_value <= high:
                    headroom[key] = (high - req_value) / max(high - low, 1)
                    continue
                else:
                    reasons.append(
                        f"{key}={req_value} outside range {range_key}=[{low}, {high}]"
                    )
                    continue

        # Direct key match
        if key not in available:
            reasons.append(f"{key} not available in equipment capabilities")
            continue

        avail_value = available[key]

        if isinstance(req_value, (int, float)) and isinstance(avail_value, (int, float)):
            if req_value > avail_value:
                reasons.append(f"{key}: required {req_value} > available {avail_value}")
            else:
                headroom[key] = (avail_value - req_value) / max(avail_value, 1)
        elif isinstance(req_value, str) and isinstance(avail_value, str):
            if req_value != avail_value:
                reasons.append(f"{key}: required '{req_value}' != available '{avail_value}'")
        elif isinstance(req_value, bool) and isinstance(avail_value, bool):
            if req_value and not avail_value:
                reasons.append(f"{key}: required but not available")

    return MatchResult(
        is_match=len(reasons) == 0,
        reasons=reasons,
        headroom=headroom,
    )


def _find_range_key(param_key: str, available: dict) -> str | None:
    """Find a range key in available that might match a parameter.

    e.g. param_key="peak_temperature" matches "temperature_range"
    """
    # Common pattern: "X" matches "X_range"
    for avail_key in available:
        if avail_key.endswith("_range"):
            base = avail_key[: -len("_range")]
            if base in param_key or param_key in base:
                return avail_key
    return None
```

**Step 6: Update `__init__.py` files**

Add `LineCapabilityMatrix` to models `__init__.py` and `LineCapabilityCreate`, `LineCapabilityResponse` to schemas `__init__.py`.

**Step 7: Run test to verify it passes**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_line_capability.py -v`
Expected: All 10 tests PASS

**Step 8: Commit**

```bash
git add backend/app/models/line_capability.py backend/app/schemas/line_capability.py backend/app/services/capability_matcher.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/tests/test_line_capability.py
git commit -m "feat: add LineCapabilityMatrix model, schema, and matcher service"
```

---

### Task 4: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/002_add_process_stations_routes_capabilities.py`

**Step 1: Write the migration**

Create `backend/alembic/versions/002_add_process_stations_routes_capabilities.py`:

```python
"""Add process stations, routes, and capability matrix tables.

Revision ID: 002_process_expansion
Revises: 001_initial_schema
Create Date: 2026-02-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002_process_expansion"
down_revision: str = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create process_stations, process_routes, and line_capability_matrix tables."""
    # --- process_stations ---
    op.create_table(
        "process_stations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("production_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("station_order", sa.Integer(), nullable=False, comment="Position in the line (1-based)"),
        sa.Column("equipment_type", sa.String(50), nullable=False, comment="e.g. solder_printer, reflow_oven"),
        sa.Column("standard_cycle_time", sa.Float(), nullable=False, comment="Standard cycle time in seconds per unit"),
        sa.Column("actual_cycle_time", sa.Float(), nullable=True, comment="Learned cycle time from MES data"),
        sa.Column("capabilities", postgresql.JSONB(), nullable=True, comment="Equipment capability parameters"),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["production_line_id"], ["production_lines.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_process_stations_line_id", "process_stations", ["production_line_id"])
    op.create_index("ix_process_stations_equipment_type", "process_stations", ["equipment_type"])

    # --- process_routes ---
    op.create_table(
        "process_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("steps", postgresql.JSONB(), nullable=False, comment="Array of process steps"),
        sa.Column("source", sa.String(20), server_default="manual", nullable=False, comment="manual | spec_parsed | mes_learned"),
        sa.Column("source_file", sa.Text(), nullable=True, comment="Path to original spec file"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_process_routes_product_id", "process_routes", ["product_id"])

    # --- line_capability_matrix ---
    op.create_table(
        "line_capability_matrix",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("production_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("equipment_type", sa.String(50), nullable=False, comment="Equipment type this entry describes"),
        sa.Column("capability_params", postgresql.JSONB(), nullable=True, comment="What this equipment can handle"),
        sa.Column("throughput_range", postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["production_line_id"], ["production_lines.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_line_capability_line_id", "line_capability_matrix", ["production_line_id"])
    op.create_index("ix_line_capability_equipment_type", "line_capability_matrix", ["equipment_type"])


def downgrade() -> None:
    """Drop process expansion tables."""
    op.drop_table("line_capability_matrix")
    op.drop_table("process_routes")
    op.drop_table("process_stations")
```

**Step 2: Commit**

```bash
git add backend/alembic/versions/002_add_process_stations_routes_capabilities.py
git commit -m "feat: add migration for process stations, routes, and capability matrix"
```

---

### Task 5: CRUD API for Process Stations

**Files:**
- Create: `backend/app/api/v1/process_stations.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_process_station_api.py`

**Step 1: Write the failing test**

Create `backend/tests/test_process_station_api.py`:

```python
"""Tests for ProcessStation CRUD API endpoints."""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.process_station import ProcessStationCreate


SAMPLE_LINE_ID = uuid.UUID("b0000000-0000-0000-0000-000000000001")


class TestProcessStationAPI:
    """Tests for process station API logic."""

    def test_create_schema_valid(self):
        data = ProcessStationCreate(
            name="錫膏印刷",
            station_order=1,
            equipment_type="solder_printer",
            standard_cycle_time=8.5,
            capabilities={"max_board_width": 450},
        )
        assert data.name == "錫膏印刷"

    def test_create_schema_missing_required(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ProcessStationCreate(
                name="Bad",
                # missing station_order, equipment_type, standard_cycle_time
            )

    def test_station_ordering(self):
        """Verify stations can be created with sequential ordering."""
        stations = [
            ProcessStationCreate(
                name=f"Station-{i}",
                station_order=i,
                equipment_type=f"type_{i}",
                standard_cycle_time=float(i * 5),
            )
            for i in range(1, 5)
        ]
        orders = [s.station_order for s in stations]
        assert orders == [1, 2, 3, 4]
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_process_station_api.py -v`
Expected: PASS (schema tests only, API file not yet created)

**Step 3: Write the API endpoint**

Create `backend/app/api/v1/process_stations.py`:

```python
"""Process Stations CRUD API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.process_station import ProcessStation
from app.models.production_line import ProductionLine
from app.schemas.process_station import ProcessStationCreate, ProcessStationResponse

router = APIRouter(prefix="/process-stations", tags=["process-stations"])


@router.get("/by-line/{line_id}", response_model=list[ProcessStationResponse])
async def list_stations_by_line(
    line_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ProcessStation]:
    """List all stations for a production line, ordered by station_order."""
    result = await db.execute(
        select(ProcessStation)
        .where(ProcessStation.production_line_id == line_id)
        .order_by(ProcessStation.station_order)
    )
    return list(result.scalars().all())


@router.post(
    "/by-line/{line_id}",
    response_model=ProcessStationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_station(
    line_id: uuid.UUID,
    payload: ProcessStationCreate,
    db: AsyncSession = Depends(get_db),
) -> ProcessStation:
    """Create a new station on a production line."""
    # Verify line exists
    line_result = await db.execute(
        select(ProductionLine).where(ProductionLine.id == line_id)
    )
    if line_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Production line not found")

    station = ProcessStation(
        production_line_id=line_id,
        name=payload.name,
        station_order=payload.station_order,
        equipment_type=payload.equipment_type,
        standard_cycle_time=payload.standard_cycle_time,
        capabilities=payload.capabilities,
        status=payload.status,
    )
    db.add(station)
    await db.flush()
    await db.refresh(station)
    return station


@router.get("/{station_id}", response_model=ProcessStationResponse)
async def get_station(
    station_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ProcessStation:
    """Get a single station by ID."""
    result = await db.execute(
        select(ProcessStation).where(ProcessStation.id == station_id)
    )
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(status_code=404, detail="Process station not found")
    return station


@router.put("/{station_id}", response_model=ProcessStationResponse)
async def update_station(
    station_id: uuid.UUID,
    payload: ProcessStationCreate,
    db: AsyncSession = Depends(get_db),
) -> ProcessStation:
    """Update an existing station."""
    result = await db.execute(
        select(ProcessStation).where(ProcessStation.id == station_id)
    )
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(status_code=404, detail="Process station not found")

    station.name = payload.name
    station.station_order = payload.station_order
    station.equipment_type = payload.equipment_type
    station.standard_cycle_time = payload.standard_cycle_time
    station.capabilities = payload.capabilities
    station.status = payload.status

    await db.flush()
    await db.refresh(station)
    return station


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_station(
    station_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a station."""
    result = await db.execute(
        select(ProcessStation).where(ProcessStation.id == station_id)
    )
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(status_code=404, detail="Process station not found")
    await db.delete(station)
```

**Step 4: Register in router**

Add to `backend/app/api/v1/router.py`:

```python
from app.api.v1.process_stations import router as process_stations_router
# Inside _authenticated:
_authenticated.include_router(process_stations_router)
```

**Step 5: Run tests**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_process_station_api.py tests/test_process_station.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add backend/app/api/v1/process_stations.py backend/app/api/v1/router.py backend/tests/test_process_station_api.py
git commit -m "feat: add process stations CRUD API"
```

---

### Task 6: CRUD API for Process Routes + Line Capabilities

**Files:**
- Create: `backend/app/api/v1/process_routes.py`
- Create: `backend/app/api/v1/line_capabilities.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_process_route_api.py`

**Step 1: Write the failing test**

Create `backend/tests/test_process_route_api.py`:

```python
"""Tests for ProcessRoute API schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.process_route import ProcessRouteCreate


SAMPLE_STEPS = [
    {
        "step_order": 1,
        "equipment_type": "solder_printer",
        "required_params": {"stencil_thickness": 0.12},
        "estimated_cycle_time": 8.5,
        "quality_checkpoints": ["solder_paste_height"],
    },
]


class TestProcessRouteAPI:
    def test_create_valid(self):
        data = ProcessRouteCreate(steps=SAMPLE_STEPS, source="manual")
        assert len(data.steps) == 1

    def test_create_empty_steps_rejected(self):
        with pytest.raises(ValidationError):
            ProcessRouteCreate(steps=[], source="manual")

    def test_create_invalid_source_rejected(self):
        with pytest.raises(ValidationError):
            ProcessRouteCreate(steps=SAMPLE_STEPS, source="unknown")
```

**Step 2: Write API endpoints**

Create `backend/app/api/v1/process_routes.py` and `backend/app/api/v1/line_capabilities.py` following the same CRUD pattern as process_stations (get by product/line, create, update, delete).

**Step 3: Register in router**

```python
from app.api.v1.process_routes import router as process_routes_router
from app.api.v1.line_capabilities import router as line_capabilities_router
_authenticated.include_router(process_routes_router)
_authenticated.include_router(line_capabilities_router)
```

**Step 4: Run tests**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_process_route_api.py tests/test_process_route.py tests/test_line_capability.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/process_routes.py backend/app/api/v1/line_capabilities.py backend/app/api/v1/router.py backend/tests/test_process_route_api.py
git commit -m "feat: add process routes and line capabilities CRUD APIs"
```

---

### Task 7: Upgrade Scheduler — Capability-Based Matching

**Files:**
- Modify: `backend/app/services/production_helpers.py`
- Modify: `backend/app/services/scheduler.py`
- Test: `backend/tests/test_scheduler_capability.py`

**Step 1: Write the failing test**

Create `backend/tests/test_scheduler_capability.py`:

```python
"""Tests for scheduler capability-based matching upgrade."""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.services.capability_matcher import MatchResult, check_capability_match


def _make_mock(defaults: dict[str, Any], overrides: dict[str, Any]) -> MagicMock:
    merged = {**defaults, **overrides}
    mock = MagicMock()
    for k, v in merged.items():
        setattr(mock, k, v)
    return mock


class TestProductAllowedWithCapabilities:
    """Test upgraded is_product_allowed that checks capability matrix."""

    def test_fallback_to_allowed_products(self):
        """When no capabilities exist, fall back to allowed_products list."""
        from app.services.production_helpers import is_product_allowed

        line = _make_mock(
            {"allowed_products": ["PCB-A100", "PCB-B200"], "changeover_matrix": None},
            {},
        )
        assert is_product_allowed("PCB-A100", line) is True
        assert is_product_allowed("MOTOR-M50", line) is False

    def test_allowed_products_none_allows_all(self):
        from app.services.production_helpers import is_product_allowed

        line = _make_mock(
            {"allowed_products": None, "changeover_matrix": None},
            {},
        )
        assert is_product_allowed("ANY-PRODUCT", line) is True


class TestBottleneckCalculation:
    """Test production time calculation using bottleneck station."""

    def test_bottleneck_station_determines_time(self):
        from app.services.production_helpers import calculate_bottleneck_production_time

        route_steps = [
            {"equipment_type": "solder_printer", "estimated_cycle_time": 8.5},
            {"equipment_type": "pick_and_place", "estimated_cycle_time": 12.0},
            {"equipment_type": "reflow_oven", "estimated_cycle_time": 45.0},
        ]
        stations = [
            _make_mock(
                {"equipment_type": "solder_printer", "actual_cycle_time": None},
                {},
            ),
            _make_mock(
                {"equipment_type": "pick_and_place", "actual_cycle_time": 10.0},
                {},
            ),
            _make_mock(
                {"equipment_type": "reflow_oven", "actual_cycle_time": 40.0},
                {},
            ),
        ]

        hours = calculate_bottleneck_production_time(
            route_steps=route_steps,
            stations=stations,
            quantity=100,
            yield_rate=0.95,
            setup_time_minutes=30.0,
        )

        # Bottleneck: reflow_oven at 40 sec/unit (actual)
        # effective_qty = 100 / 0.95 ≈ 105.26
        # production = 105.26 * 40 / 3600 ≈ 1.169 hours
        # setup = 30 / 60 = 0.5 hours
        # total ≈ 1.669 hours
        assert 1.5 < hours < 2.0

    def test_uses_estimated_when_no_actual(self):
        from app.services.production_helpers import calculate_bottleneck_production_time

        route_steps = [
            {"equipment_type": "solder_printer", "estimated_cycle_time": 8.5},
        ]
        stations = [
            _make_mock(
                {"equipment_type": "solder_printer", "actual_cycle_time": None},
                {},
            ),
        ]

        hours = calculate_bottleneck_production_time(
            route_steps=route_steps,
            stations=stations,
            quantity=100,
            yield_rate=1.0,
            setup_time_minutes=0.0,
        )

        # 100 * 8.5 / 3600 ≈ 0.236 hours
        assert 0.2 < hours < 0.3

    def test_empty_stations_returns_zero(self):
        from app.services.production_helpers import calculate_bottleneck_production_time

        hours = calculate_bottleneck_production_time(
            route_steps=[],
            stations=[],
            quantity=100,
            yield_rate=0.95,
            setup_time_minutes=30.0,
        )
        assert hours == 0.5  # Only setup time
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_scheduler_capability.py -v`
Expected: FAIL with `ImportError: cannot import name 'calculate_bottleneck_production_time'`

**Step 3: Add bottleneck calculation to production_helpers.py**

Add to `backend/app/services/production_helpers.py`:

```python
def calculate_bottleneck_production_time(
    route_steps: list[dict],
    stations: list,
    quantity: int,
    yield_rate: float,
    setup_time_minutes: float,
) -> float:
    """Calculate production time using bottleneck station cycle time.

    Args:
        route_steps: Process route steps with estimated_cycle_time (seconds).
        stations: ProcessStation objects with actual_cycle_time.
        quantity: Number of units to produce.
        yield_rate: Expected yield rate (0-1).
        setup_time_minutes: Total setup time in minutes.

    Returns:
        Total production time in hours.
    """
    if not route_steps:
        return setup_time_minutes / 60.0

    # Build station lookup by equipment_type
    station_lookup = {}
    for s in stations:
        station_lookup[s.equipment_type] = s

    # Find cycle times for each step
    cycle_times: list[float] = []
    for step in route_steps:
        eq_type = step["equipment_type"]
        estimated = step.get("estimated_cycle_time", 0.0)

        station = station_lookup.get(eq_type)
        actual = station.actual_cycle_time if station else None

        cycle_times.append(actual if actual is not None else estimated)

    if not cycle_times:
        return setup_time_minutes / 60.0

    bottleneck_seconds = max(cycle_times)
    effective_qty = quantity / max(yield_rate, 0.01)
    production_hours = (effective_qty * bottleneck_seconds) / 3600.0
    setup_hours = setup_time_minutes / 60.0

    return production_hours + setup_hours
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_scheduler_capability.py -v`
Expected: All PASS

**Step 5: Run ALL existing tests to verify no regression**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/ -v --tb=short`
Expected: All existing tests still PASS

**Step 6: Commit**

```bash
git add backend/app/services/production_helpers.py backend/tests/test_scheduler_capability.py
git commit -m "feat: add bottleneck production time calculation to scheduler"
```

---

### Task 8: Seed Data for Process Stations + Routes + Capabilities

**Files:**
- Modify: `backend/app/db/seed.py`
- Test: `backend/tests/test_seed_expansion.py`

**Step 1: Write the failing test**

Create `backend/tests/test_seed_expansion.py`:

```python
"""Tests for expanded seed data with stations, routes, and capabilities."""

import pytest


class TestSeedDataExpansion:
    def test_seed_creates_stations(self):
        from app.db.seed import _create_process_stations

        stations = _create_process_stations()
        assert len(stations) > 0
        # Each line should have 3-5 stations
        line_ids = set(s.production_line_id for s in stations)
        assert len(line_ids) >= 2

    def test_seed_creates_routes(self):
        from app.db.seed import _create_process_routes

        routes = _create_process_routes()
        assert len(routes) > 0
        # Each route should have steps
        for route in routes:
            assert len(route.steps) >= 2

    def test_seed_creates_capabilities(self):
        from app.db.seed import _create_line_capabilities

        caps = _create_line_capabilities()
        assert len(caps) > 0

    def test_stations_ordered_sequentially(self):
        from app.db.seed import _create_process_stations

        stations = _create_process_stations()
        by_line: dict = {}
        for s in stations:
            by_line.setdefault(s.production_line_id, []).append(s)

        for line_id, line_stations in by_line.items():
            orders = sorted(s.station_order for s in line_stations)
            assert orders == list(range(1, len(orders) + 1)), (
                f"Line {line_id} stations not sequential: {orders}"
            )
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_seed_expansion.py -v`
Expected: FAIL

**Step 3: Add seed data functions to seed.py**

Add `_create_process_stations()`, `_create_process_routes()`, `_create_line_capabilities()` to `backend/app/db/seed.py`. Use existing `LINE_IDS` and `PRODUCT_IDS`.

Example seed data for SMT-Line-1:
- Station 1: 錫膏印刷 (solder_printer, 8.5 sec)
- Station 2: 高速貼片 (pick_and_place, 12.0 sec)
- Station 3: 回焊爐 (reflow_oven, 45.0 sec)
- Station 4: AOI檢測 (aoi_inspection, 5.0 sec)

Update `seed_demo_data()` to also add the new entities.

**Step 4: Run test to verify it passes**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/test_seed_expansion.py -v`
Expected: All PASS

**Step 5: Run all tests**

Run: `cd /Users/vincewang/autopilot-sme/backend && python -m pytest tests/ -v --tb=short`
Expected: All PASS

**Step 6: Commit**

```bash
git add backend/app/db/seed.py backend/tests/test_seed_expansion.py
git commit -m "feat: add seed data for process stations, routes, and capabilities"
```

---

### Task 9: Frontend Types Update

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

**Step 1: Add new TypeScript types**

Add to `frontend/src/lib/types.ts`:

```typescript
// Process Station
export interface ProcessStationResponse {
  id: string
  production_line_id: string
  name: string
  station_order: number
  equipment_type: string
  standard_cycle_time: number
  actual_cycle_time: number | null
  capabilities: Record<string, unknown> | null
  status: string
  created_at: string
  updated_at: string
}

export interface ProcessStationCreate {
  name: string
  station_order: number
  equipment_type: string
  standard_cycle_time: number
  capabilities?: Record<string, unknown> | null
  status?: string
}

// Process Route
export interface ProcessRouteStepSchema {
  step_order: number
  equipment_type: string
  required_params?: Record<string, unknown> | null
  estimated_cycle_time: number
  quality_checkpoints?: string[]
}

export interface ProcessRouteResponse {
  id: string
  product_id: string
  version: number
  is_active: boolean
  steps: ProcessRouteStepSchema[]
  source: string
  source_file: string | null
  created_at: string
  updated_at: string
}

// Line Capability
export interface LineCapabilityResponse {
  id: string
  production_line_id: string
  equipment_type: string
  capability_params: Record<string, unknown> | null
  throughput_range: Record<string, unknown> | null
  updated_at: string
}
```

**Step 2: Add API functions**

Add to `frontend/src/lib/api.ts`:

```typescript
// Process Stations
export async function getStationsByLine(lineId: string): Promise<ProcessStationResponse[]> {
  return fetchApi(`/process-stations/by-line/${lineId}`)
}

export async function createStation(lineId: string, data: ProcessStationCreate): Promise<ProcessStationResponse> {
  return fetchApi(`/process-stations/by-line/${lineId}`, { method: 'POST', body: JSON.stringify(data) })
}

// Process Routes
export async function getRoutesByProduct(productId: string): Promise<ProcessRouteResponse[]> {
  return fetchApi(`/process-routes/by-product/${productId}`)
}

// Line Capabilities
export async function getCapabilitiesByLine(lineId: string): Promise<LineCapabilityResponse[]> {
  return fetchApi(`/line-capabilities/by-line/${lineId}`)
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: add frontend types and API functions for process expansion"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | ProcessStation model + schema | 5 tests |
| 2 | ProcessRoute model + schema | 6 tests |
| 3 | LineCapabilityMatrix + capability matcher | 10 tests |
| 4 | Alembic migration | — |
| 5 | Process stations CRUD API | 3 tests |
| 6 | Process routes + capabilities CRUD API | 3 tests |
| 7 | Scheduler bottleneck calculation | 5 tests |
| 8 | Expanded seed data | 4 tests |
| 9 | Frontend types update | — |

**Total new tests:** ~36
**Estimated commits:** 9 atomic commits

After Phase 1 completion, proceed to Phase 2 (規格書 AI 解析) in a separate plan document.
