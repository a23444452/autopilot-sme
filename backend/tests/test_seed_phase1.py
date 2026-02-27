"""Tests for Phase 1 seed data (process stations, routes, capabilities)."""

from app.db.seed import (
    _create_line_capabilities,
    _create_process_routes,
    _create_process_stations,
)


class TestSeedProcessStations:
    def test_creates_stations_for_all_lines(self):
        stations = _create_process_stations()
        assert len(stations) == 14  # 3 + 4 + 3 + 4

    def test_station_orders_sequential(self):
        stations = _create_process_stations()
        from app.db.seed import LINE_IDS

        smt1_stations = [s for s in stations if s.production_line_id == LINE_IDS["SMT-Line-1"]]
        orders = [s.station_order for s in smt1_stations]
        assert orders == [1, 2, 3]

    def test_all_stations_active(self):
        stations = _create_process_stations()
        assert all(s.status == "active" for s in stations)


class TestSeedProcessRoutes:
    def test_creates_routes_for_all_products(self):
        routes = _create_process_routes()
        assert len(routes) == 6  # one per product

    def test_all_routes_active(self):
        routes = _create_process_routes()
        assert all(r.is_active for r in routes)

    def test_all_routes_manual_source(self):
        routes = _create_process_routes()
        assert all(r.source == "manual" for r in routes)

    def test_steps_not_empty(self):
        routes = _create_process_routes()
        assert all(len(r.steps) >= 2 for r in routes)


class TestSeedLineCapabilities:
    def test_creates_capabilities(self):
        caps = _create_line_capabilities()
        assert len(caps) == 14  # 3 + 4 + 3 + 4

    def test_all_have_equipment_type(self):
        caps = _create_line_capabilities()
        assert all(c.equipment_type for c in caps)

    def test_all_have_capability_params(self):
        caps = _create_line_capabilities()
        assert all(c.capability_params is not None for c in caps)
