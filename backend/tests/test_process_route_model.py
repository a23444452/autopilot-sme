"""Tests that ProcessRoute model is importable and has correct columns."""

from app.models.process_route import ProcessRoute


def test_process_route_has_required_columns():
    mapper = ProcessRoute.__mapper__
    col_names = {c.key for c in mapper.columns}
    assert "id" in col_names
    assert "product_id" in col_names
    assert "version" in col_names
    assert "is_active" in col_names
    assert "steps" in col_names
    assert "source" in col_names
    assert "source_file" in col_names
    assert "created_at" in col_names
    assert "updated_at" in col_names


def test_process_route_tablename():
    assert ProcessRoute.__tablename__ == "process_routes"
