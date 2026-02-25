"""Tests that LineCapabilityMatrix model is importable and has correct columns."""

from app.models.line_capability import LineCapabilityMatrix


def test_line_capability_has_required_columns():
    mapper = LineCapabilityMatrix.__mapper__
    col_names = {c.key for c in mapper.columns}
    assert "id" in col_names
    assert "production_line_id" in col_names
    assert "equipment_type" in col_names
    assert "capability_params" in col_names
    assert "throughput_range" in col_names
    assert "updated_at" in col_names


def test_line_capability_tablename():
    assert LineCapabilityMatrix.__tablename__ == "line_capability_matrix"
