"""Tests for LineCapabilityMatrix Pydantic schemas."""

import uuid
from datetime import datetime, timezone

from app.schemas.line_capability import LineCapabilityCreate, LineCapabilityResponse


class TestLineCapabilityCreate:
    def test_valid_minimal(self):
        lc = LineCapabilityCreate(
            production_line_id=uuid.uuid4(),
            equipment_type="SMT",
        )
        assert lc.capability_params is None
        assert lc.throughput_range is None

    def test_with_all_fields(self):
        lc = LineCapabilityCreate(
            production_line_id=uuid.uuid4(),
            equipment_type="SMT",
            capability_params={"max_speed_rpm": 3000},
            throughput_range={"min_units_per_hour": 50, "max_units_per_hour": 120},
        )
        assert lc.capability_params["max_speed_rpm"] == 3000


class TestLineCapabilityResponse:
    def test_from_attributes(self):
        now = datetime.now(timezone.utc)
        r = LineCapabilityResponse(
            id=uuid.uuid4(),
            production_line_id=uuid.uuid4(),
            equipment_type="SMT",
            capability_params=None,
            throughput_range=None,
            updated_at=now,
        )
        assert r.equipment_type == "SMT"
