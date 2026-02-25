"""Tests for ProcessStation Pydantic schemas."""

import uuid
from datetime import datetime, timezone

import pytest

from app.schemas.process_station import ProcessStationCreate, ProcessStationResponse


class TestProcessStationCreate:
    def test_valid_minimal(self):
        s = ProcessStationCreate(
            production_line_id=uuid.uuid4(),
            name="SMT Station 1",
            station_order=1,
            equipment_type="SMT",
            standard_cycle_time=45.0,
        )
        assert s.status == "active"
        assert s.actual_cycle_time is None

    def test_station_order_must_be_positive(self):
        with pytest.raises(Exception):
            ProcessStationCreate(
                production_line_id=uuid.uuid4(),
                name="Bad",
                station_order=0,
                equipment_type="SMT",
                standard_cycle_time=10.0,
            )

    def test_cycle_time_must_be_positive(self):
        with pytest.raises(Exception):
            ProcessStationCreate(
                production_line_id=uuid.uuid4(),
                name="Bad",
                station_order=1,
                equipment_type="SMT",
                standard_cycle_time=-1.0,
            )


class TestProcessStationResponse:
    def test_from_attributes(self):
        now = datetime.now(timezone.utc)
        r = ProcessStationResponse(
            id=uuid.uuid4(),
            production_line_id=uuid.uuid4(),
            name="Station A",
            station_order=1,
            equipment_type="SMT",
            standard_cycle_time=45.0,
            actual_cycle_time=None,
            capabilities=None,
            status="active",
            created_at=now,
            updated_at=now,
        )
        assert r.status == "active"
