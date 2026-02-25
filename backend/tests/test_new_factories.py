"""Tests for Phase 1 test factories (ProcessStation, ProcessRoute, LineCapability)."""


class TestProcessStationFactory:
    def test_creates_with_defaults(self, station_factory):
        s = station_factory.create()
        assert s.name == "Station-1"
        assert s.station_order == 1
        assert s.equipment_type == "SMT"
        assert s.standard_cycle_time == 45.0
        assert s.status == "active"

    def test_override_fields(self, station_factory):
        s = station_factory.create(name="Custom", equipment_type="reflow", standard_cycle_time=120.0)
        assert s.name == "Custom"
        assert s.equipment_type == "reflow"
        assert s.standard_cycle_time == 120.0

    def test_counter_increments(self, station_factory):
        s1 = station_factory.create()
        s2 = station_factory.create()
        assert s1.station_order == 1
        assert s2.station_order == 2
        assert s1.id != s2.id


class TestProcessRouteFactory:
    def test_creates_with_defaults(self, route_factory):
        r = route_factory.create()
        assert r.version == 1
        assert r.is_active is True
        assert r.source == "manual"
        assert len(r.steps) == 2

    def test_override_steps(self, route_factory):
        custom_steps = [{"station_order": 1, "equipment_type": "CNC", "cycle_time_sec": 60.0}]
        r = route_factory.create(steps=custom_steps)
        assert len(r.steps) == 1
        assert r.steps[0]["equipment_type"] == "CNC"


class TestLineCapabilityFactory:
    def test_creates_with_defaults(self, capability_factory):
        c = capability_factory.create()
        assert c.equipment_type == "SMT"
        assert c.capability_params is None
        assert c.throughput_range is None

    def test_override_params(self, capability_factory):
        c = capability_factory.create(
            equipment_type="reflow",
            capability_params={"max_temp": 260},
            throughput_range={"min": 50, "max": 120},
        )
        assert c.equipment_type == "reflow"
        assert c.capability_params["max_temp"] == 260
