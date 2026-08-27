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


def test_extract_carbon_price_recognises_common_shapes():
    assert live_data._extract_carbon_price({"price_usd_per_tco2": 72.5}) == 72.5
    assert live_data._extract_carbon_price({"price": "68.1"}) == 68.1
    assert live_data._extract_carbon_price({"value": 55}) == 55.0
    assert live_data._extract_carbon_price({"data": [{"close": 80.0}]}) == 80.0
    assert live_data._extract_carbon_price({"results": {"last": 91.2}}) == 91.2
    assert live_data._extract_carbon_price([{"price": 63.4}, {"price": 64.9}]) == 64.9
    assert live_data._extract_carbon_price({"unrelated": "nope"}) is None
    assert live_data._extract_carbon_price("not json-ish") is None


def test_extract_carbon_price_is_case_insensitive():
    # Trading Economics and several other providers title-case their keys.
    assert live_data._extract_carbon_price({"Last": 82.3}) == 82.3
    assert live_data._extract_carbon_price({"Close": "79.4"}) == 79.4
    assert live_data._extract_carbon_price([{"Symbol": "CFI2", "Last": 83.1}]) == 83.1


def test_live_carbon_feed_used_when_url_configured(monkeypatch):
    monkeypatch.setenv("ALPHA_LIVE_DATA", "1")
    monkeypatch.setenv("CARBON_PRICE_URL", "https://example.invalid/carbon")
    monkeypatch.delenv("CARBON_PRICE_USD_PER_TCO2", raising=False)
    live_data._cache.clear()
    monkeypatch.setattr(live_data, "_fetch_json", lambda url, timeout=6.0: {"price": 77.0, "as_of": "2026-08-26"})
    price, meta = live_data.get_carbon_price()
    assert price == 77.0
    assert meta["live"] is True
    assert meta["as_of"] == "2026-08-26"


def test_live_carbon_feed_implausible_value_falls_back(monkeypatch):
    monkeypatch.setenv("ALPHA_LIVE_DATA", "1")
    monkeypatch.setenv("CARBON_PRICE_URL", "https://example.invalid/carbon")
    monkeypatch.delenv("CARBON_PRICE_USD_PER_TCO2", raising=False)
    live_data._cache.clear()
    monkeypatch.setattr(live_data, "_fetch_json", lambda url, timeout=6.0: {"price": 99999.0})
    price, meta = live_data.get_carbon_price()
    assert price == CARBON_PRICE_USD_PER_TCO2
    assert meta["live"] is False


def test_live_carbon_feed_unrecognised_shape_falls_back(monkeypatch):
    monkeypatch.setenv("ALPHA_LIVE_DATA", "1")
    monkeypatch.setenv("CARBON_PRICE_URL", "https://example.invalid/carbon")
    monkeypatch.delenv("CARBON_PRICE_USD_PER_TCO2", raising=False)
    live_data._cache.clear()
    monkeypatch.setattr(live_data, "_fetch_json", lambda url, timeout=6.0: {"unrelated_field": "nope"})
    price, meta = live_data.get_carbon_price()
    assert price == CARBON_PRICE_USD_PER_TCO2
    assert meta["live"] is False


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
