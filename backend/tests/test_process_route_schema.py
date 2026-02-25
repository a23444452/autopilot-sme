"""Tests for ProcessRoute Pydantic schemas."""

import uuid
from datetime import datetime, timezone

import pytest

from app.schemas.process_route import ProcessRouteCreate, ProcessRouteResponse


VALID_STEPS = [
    {"station_order": 1, "equipment_type": "SMT", "cycle_time_sec": 45.0},
    {"station_order": 2, "equipment_type": "reflow", "cycle_time_sec": 120.0},
]


class TestProcessRouteCreate:
    def test_valid_defaults(self):
        r = ProcessRouteCreate(
            product_id=uuid.uuid4(),
            steps=VALID_STEPS,
        )
        assert r.version == 1
        assert r.is_active is True
        assert r.source == "manual"

    def test_invalid_source(self):
        with pytest.raises(Exception):
            ProcessRouteCreate(
                product_id=uuid.uuid4(),
                steps=VALID_STEPS,
                source="unknown_source",
            )

    def test_steps_must_not_be_empty(self):
        with pytest.raises(Exception):
            ProcessRouteCreate(
                product_id=uuid.uuid4(),
                steps=[],
            )


class TestProcessRouteResponse:
    def test_from_attributes(self):
        now = datetime.now(timezone.utc)
        r = ProcessRouteResponse(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            version=1,
            is_active=True,
            steps=VALID_STEPS,
            source="manual",
            source_file=None,
            created_at=now,
            updated_at=now,
        )
        assert r.source == "manual"
