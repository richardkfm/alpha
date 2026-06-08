"""Tests for the Phase 2 valuation engine.

Run from the backend/ directory:  python -m pytest
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reference_data import CURRENCIES  # noqa: E402
from valuation import compute_valuation, geodesic_area_sqm  # noqa: E402


def _square_one_degree_at_equator():
    """A 1°×1° polygon anchored at the equator (lon 0..1, lat 0..1)."""
    return {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }


def test_area_one_degree_square_at_equator():
    # ~111.2 km per degree => roughly 1.23e10 m^2. Allow a few % tolerance.
    area = geodesic_area_sqm(_square_one_degree_at_equator())
    assert math.isclose(area, 1.232e10, rel_tol=0.02), area


def test_multipolygon_area_is_sum_of_parts():
    poly = _square_one_degree_at_equator()
    single = geodesic_area_sqm(poly)
    multi = geodesic_area_sqm(
        {
            "type": "MultiPolygon",
            "coordinates": [poly["coordinates"], poly["coordinates"]],
        }
    )
    assert math.isclose(multi, 2 * single, rel_tol=1e-9)


def test_hole_is_subtracted():
    outer = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    hole = [[0.25, 0.25], [0.75, 0.25], [0.75, 0.75], [0.25, 0.75], [0.25, 0.25]]
    with_hole = geodesic_area_sqm({"type": "Polygon", "coordinates": [outer, hole]})
    without = geodesic_area_sqm({"type": "Polygon", "coordinates": [outer]})
    assert with_hole < without


def test_feature_is_unwrapped():
    feature = {"type": "Feature", "geometry": _square_one_degree_at_equator()}
    assert geodesic_area_sqm(feature) > 0


def test_tev_per_sqm_matches_reference_sum():
    # 1 ha tropical rainforest: 0.0069+0.036+0.02+0.05+0.012 = 0.1249 USD/m2/yr.
    res = compute_valuation(_square_one_degree_at_equator(), "tropical_rainforest", "USD")
    assert math.isclose(res["total_ecosystem_value_per_sqm_year"], 0.1249, abs_tol=1e-6)
    assert math.isclose(
        res["total_ecosystem_value_per_sqm_year"],
        sum(res["yields_per_sqm_year"].values()),
        abs_tol=1e-6,
    )


def test_total_scales_with_area():
    res = compute_valuation(_square_one_degree_at_equator(), "tropical_rainforest", "USD")
    expected = res["total_ecosystem_value_per_sqm_year"] * res["area"]["sqm"]
    assert math.isclose(res["total_ecosystem_value_per_year"], expected, rel_tol=1e-6)


def test_currency_conversion_applies_fx():
    usd = compute_valuation(_square_one_degree_at_equator(), "tropical_rainforest", "USD")
    eur = compute_valuation(_square_one_degree_at_equator(), "tropical_rainforest", "EUR")
    rate = CURRENCIES["EUR"]["rate_per_usd"]
    assert eur["currency"] == "EUR"
    assert eur["currency_symbol"] == "€"
    assert math.isclose(
        eur["total_ecosystem_value_per_sqm_year"],
        usd["total_ecosystem_value_per_sqm_year"] * rate,
        rel_tol=1e-4,
    )


def test_unknown_biome_and_currency_fall_back_to_defaults():
    res = compute_valuation(_square_one_degree_at_equator(), "atlantis", "XYZ")
    assert res["biome_key"] == "tropical_rainforest"
    assert res["currency"] == "USD"


def test_capitalized_value_is_annual_over_discount_rate():
    res = compute_valuation(_square_one_degree_at_equator(), "tropical_rainforest", "USD")
    cap = res["capitalized_value"]
    expected = res["total_ecosystem_value_per_year"] / cap["discount_rate"]
    assert math.isclose(cap["asset_value_total"], expected, rel_tol=1e-6)


def test_intactness_scales_realised_value_but_not_potential():
    full = compute_valuation(_square_one_degree_at_equator(), "wetland", "USD")
    half = compute_valuation(_square_one_degree_at_equator(), "wetland", "USD", intactness=0.5)
    assert half["intactness"] == 0.5
    # realised value halves; the intact ceiling is reported unchanged
    assert math.isclose(
        half["total_ecosystem_value_per_sqm_year"],
        full["total_ecosystem_value_per_sqm_year"] * 0.5,
        rel_tol=1e-6,
    )
    assert math.isclose(
        half["potential"]["total_ecosystem_value_per_sqm_year"],
        full["total_ecosystem_value_per_sqm_year"],
        rel_tol=1e-9,
    )


def test_default_intactness_is_one_preserving_phase2_behaviour():
    res = compute_valuation(_square_one_degree_at_equator(), "tropical_rainforest", "USD")
    assert res["intactness"] == 1.0
    assert math.isclose(res["total_ecosystem_value_per_sqm_year"], 0.1249, abs_tol=1e-6)


def test_new_ordinary_biomes_are_available():
    poly = _square_one_degree_at_equator()
    for biome in ("boreal_forest", "cropland", "freshwater", "peri_urban"):
        res = compute_valuation(poly, biome, "USD")
        assert res["biome_key"] == biome
        assert res["total_ecosystem_value_per_sqm_year"] > 0


def test_freshwater_is_water_dominated():
    res = compute_valuation(_square_one_degree_at_equator(), "freshwater", "USD")
    yields = res["yields_per_sqm_year"]
    assert yields["water_filtration"] == max(yields.values())


def test_cropland_below_wetland():
    poly = _square_one_degree_at_equator()
    cropland = compute_valuation(poly, "cropland", "USD")
    wetland = compute_valuation(poly, "wetland", "USD")
    assert (
        cropland["total_ecosystem_value_per_sqm_year"]
        < wetland["total_ecosystem_value_per_sqm_year"]
    )


def test_mangrove_values_exceed_grassland():
    poly = _square_one_degree_at_equator()
    mangrove = compute_valuation(poly, "mangrove", "USD")
    grassland = compute_valuation(poly, "temperate_grassland", "USD")
    assert (
        mangrove["total_ecosystem_value_per_sqm_year"]
        > grassland["total_ecosystem_value_per_sqm_year"]
    )
