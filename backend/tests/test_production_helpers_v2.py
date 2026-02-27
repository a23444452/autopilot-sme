"""Tests for new production_helpers functions (Phase 1 additions)."""

from unittest.mock import MagicMock

import pytest

from app.services.production_helpers import (
    calculate_production_time,
    is_product_allowed,
    is_product_allowed_with_capabilities,
)


class TestCalculateProductionTime:
    def test_empty_steps_returns_zero(self):
        assert calculate_production_time([], 100) == 0.0

    def test_bottleneck_determines_time(self):
        steps = [
            {"cycle_time_sec": 30.0},
            {"cycle_time_sec": 120.0},  # bottleneck
            {"cycle_time_sec": 45.0},
        ]
        # 120 sec/unit * 100 units / 60 = 200 minutes
        result = calculate_production_time(steps, 100)
        assert result == pytest.approx(200.0)

    def test_yield_rate_adjusts_quantity(self):
        steps = [{"cycle_time_sec": 60.0}]
        # effective_qty = 100 / 0.5 = 200, time = 60 * 200 / 60 = 200 min
        result = calculate_production_time(steps, 100, yield_rate=0.5)
        assert result == pytest.approx(200.0)

    def test_efficiency_factor_adjusts_time(self):
        steps = [{"cycle_time_sec": 60.0}]
        # time = 60 * 100 / 0.5 / 60 = 200 min
        result = calculate_production_time(steps, 100, efficiency_factor=0.5)
        assert result == pytest.approx(200.0)

    def test_uses_actual_cycle_time_when_available(self):
        steps = [
            {"cycle_time_sec": 60.0, "actual_cycle_time_sec": 90.0},  # actual is bottleneck
            {"cycle_time_sec": 120.0},
        ]
        # bottleneck = max(90, 120) = 120
        result = calculate_production_time(steps, 10)
        assert result == pytest.approx(20.0)

    def test_actual_cycle_time_none_falls_back(self):
        steps = [
            {"cycle_time_sec": 60.0, "actual_cycle_time_sec": None},
        ]
        result = calculate_production_time(steps, 60)
        assert result == pytest.approx(60.0)


class TestIsProductAllowedWithCapabilities:
    def test_falls_back_when_no_required_types(self):
        line = MagicMock()
        line.allowed_products = None
        assert is_product_allowed_with_capabilities("SKU-1", line, None, None) is True

    def test_falls_back_when_empty_required_types(self):
        line = MagicMock()
        line.allowed_products = ["SKU-1"]
        assert is_product_allowed_with_capabilities("SKU-1", line, [], None) is True

    def test_matches_when_all_types_present(self):
        line = MagicMock()
        required = ["SMT", "reflow"]
        line_types = {"SMT", "reflow", "AOI"}
        assert is_product_allowed_with_capabilities("SKU-1", line, required, line_types) is True

    def test_rejects_when_missing_type(self):
        line = MagicMock()
        required = ["SMT", "reflow"]
        line_types = {"SMT", "AOI"}
        assert is_product_allowed_with_capabilities("SKU-1", line, required, line_types) is False

    def test_fallback_uses_is_product_allowed(self):
        line = MagicMock()
        line.allowed_products = {"skus": ["SKU-A"]}
        # required_types=None -> falls back
        assert is_product_allowed_with_capabilities("SKU-A", line, None, {"SMT"}) is True
        assert is_product_allowed_with_capabilities("SKU-B", line, None, {"SMT"}) is False
