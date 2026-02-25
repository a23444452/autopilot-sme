"""Tests that ProcessStation model is importable and has correct columns."""

from app.models.process_station import ProcessStation


def test_process_station_has_required_columns():
    mapper = ProcessStation.__mapper__
    col_names = {c.key for c in mapper.columns}
    assert "id" in col_names
    assert "production_line_id" in col_names
    assert "name" in col_names
    assert "station_order" in col_names
    assert "equipment_type" in col_names
    assert "standard_cycle_time" in col_names
    assert "actual_cycle_time" in col_names
    assert "capabilities" in col_names
    assert "status" in col_names
    assert "created_at" in col_names
    assert "updated_at" in col_names


def test_process_station_tablename():
    assert ProcessStation.__tablename__ == "process_stations"
