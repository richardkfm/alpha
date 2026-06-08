"""Tests for the Phase 4 live market-data layer (offline / deterministic).

These never hit the network: they exercise the disabled-default and
operator-override paths plus the injection contract with the valuation engine.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import live_data  # noqa: E402
from reference_data import CARBON_PRICE_USD_PER_TCO2, CURRENCIES  # noqa: E402
from valuation import compute_valuation  # noqa: E402

SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}


def test_disabled_by_default_returns_static(monkeypatch):
    monkeypatch.delenv("ALPHA_LIVE_DATA", raising=False)
    monkeypatch.delenv("CARBON_PRICE_USD_PER_TCO2", raising=False)
    assert not live_data.live_enabled()
    price, meta = live_data.get_carbon_price()
    assert price == CARBON_PRICE_USD_PER_TCO2
    assert meta["live"] is False
    rates, fx_meta = live_data.get_fx_rates()
    assert rates["EUR"] == CURRENCIES["EUR"]["rate_per_usd"]
    assert fx_meta["live"] is False


def test_carbon_override_env(monkeypatch):
    monkeypatch.setenv("CARBON_PRICE_USD_PER_TCO2", "85.5")
    price, meta = live_data.get_carbon_price()
    assert price == 85.5
    assert meta["live"] is True


def test_market_snapshot_shape(monkeypatch):
    monkeypatch.delenv("ALPHA_LIVE_DATA", raising=False)
    snap = live_data.market_snapshot()
    assert "carbon" in snap and "fx" in snap
    assert "price_usd_per_tco2" in snap["carbon"]
    assert snap["fx"]["rates_per_usd"]["USD"] == 1.0


def test_injected_carbon_price_scales_carbon_yield():
    base = compute_valuation(SQUARE, "tropical_rainforest", "USD")
    doubled = compute_valuation(
        SQUARE, "tropical_rainforest", "USD", carbon_price=CARBON_PRICE_USD_PER_TCO2 * 2
    )
    assert math.isclose(
        doubled["yields_per_sqm_year"]["carbon_capture"],
        base["yields_per_sqm_year"]["carbon_capture"] * 2,
        rel_tol=1e-6,
    )
    # the other categories are unaffected by the carbon price
    assert math.isclose(
        doubled["yields_per_sqm_year"]["water_filtration"],
        base["yields_per_sqm_year"]["water_filtration"],
        rel_tol=1e-9,
    )


def test_injected_fx_rate_overrides_static():
    res = compute_valuation(SQUARE, "tropical_rainforest", "EUR", fx_rate=2.0, fx_as_of="2030-01-01")
    usd = compute_valuation(SQUARE, "tropical_rainforest", "USD")
    assert math.isclose(
        res["total_ecosystem_value_per_sqm_year"],
        usd["total_ecosystem_value_per_sqm_year"] * 2.0,
        rel_tol=1e-6,
    )
    assert res["fx"]["as_of"] == "2030-01-01"
