"""Verify that migration 002 has correct upgrade/downgrade structure."""

import ast
from pathlib import Path

MIGRATION_FILE = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "002_process_stations_routes.py"
)


def _parse_module() -> ast.Module:
    return ast.parse(MIGRATION_FILE.read_text())


def test_migration_002_file_exists():
    assert MIGRATION_FILE.exists(), f"Migration file not found: {MIGRATION_FILE}"


def test_migration_002_revision():
    tree = _parse_module()
    assignments: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in ("revision", "down_revision") and node.value:
                assignments[node.target.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in ("revision", "down_revision"):
                assignments[target.id] = ast.literal_eval(node.value)
    assert assignments["revision"] == "002_process_stations_routes"
    assert assignments["down_revision"] == "001_initial_schema"


def test_migration_002_has_upgrade_and_downgrade():
    tree = _parse_module()
    func_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "upgrade" in func_names
    assert "downgrade" in func_names
