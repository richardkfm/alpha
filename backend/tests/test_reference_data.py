"""Pins the recalibrated reference coefficients and the invariants they rest on.

Changing a coefficient should be a deliberate act: update the evidence in
``reference_data.py``, the table in ``METHODOLOGY.md`` and the pins below together.
"""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import reference_data as rd  # noqa: E402
from valuation import compute_valuation  # noqa: E402

# biome -> (sequestration tCO2/ha/yr, climate, water, biodiversity, soil) in
# 2024 USD/ha/yr. Mirrors the table in backend/METHODOLOGY.md §3.
PINNED = {
    "tropical_rainforest": (2.4, 6, 11, 569, 17),
    "temperate_forest": (3.2, 294, 47, 714, 50),
    "boreal_forest": (1.0, 180, 0, 259, 150),
    "mangrove": (5.9, 1116, 147, 4987, 2522),
    "wetland": (1.0, 1035, 186, 82, 250),
    "freshwater": (0.0, 626, 183, 404, 0),
    "temperate_grassland": (0.5, 1, 2, 59, 200),
    "cropland": (0.0, 179, 77, 393, 17),
    "peri_urban": (0.6, 1796, 56, 219, 120),
    "tundra": (0.0, 40, 30, 60, 0),
    "desert": (0.1, 3, 10, 0, 20),
}

# biome -> one-time carbon debt at full intactness, tCO2/ha.
PINNED_CARBON_DEBT = {
    "tropical_rainforest": 558.7,
    "temperate_forest": 262.7,
    "boreal_forest": 430.9,
    "mangrove": 1357.7,
    "wetland": 736.5,
    "freshwater": 0.0,
    "temperate_grassland": 99.1,
    "cropland": 45.1,
    "peri_urban": 45.1,
    "tundra": 95.6,
    "desert": 16.6,
}

POLY_1HA_ISH = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}


# --- pinned values -----------------------------------------------------------

@pytest.mark.parametrize("biome", sorted(PINNED))
def test_coefficients_are_pinned(biome):
    seq, climate, water, bio, soil = PINNED[biome]
    b = rd.BIOMES[biome]
    assert b["sequestration_tco2_ha_yr"] == seq
    assert b["climate_regulation_usd_ha_yr"] == climate
    assert b["water_filtration_usd_ha_yr"] == water
    assert b["biodiversity_premium_usd_ha_yr"] == bio
    assert b["soil_nutrient_value_usd_ha_yr"] == soil


def test_pins_cover_every_biome():
    assert set(PINNED) == set(rd.BIOMES)


def test_carbon_price_reference():
    assert rd.CARBON_PRICE_USD_PER_TCO2 == 80.0


@pytest.mark.parametrize("biome", sorted(PINNED_CARBON_DEBT))
def test_carbon_debt_is_pinned(biome):
    assert math.isclose(rd.biome_carbon_debt_tco2_ha(biome), PINNED_CARBON_DEBT[biome], abs_tol=0.05)


# --- provenance --------------------------------------------------------------

def test_every_biome_is_in_every_per_biome_table():
    keys = set(rd.BIOMES)
    for table in (
        rd.SEQUESTRATION,
        rd.BIOME_CARBON_POOLS,
        rd.BIOME_DEFAULT_INTACTNESS,
        rd.BIOME_SCARCITY_WEIGHT,
        rd.BIOME_RED_LINES,
        rd.BIOME_CARBON_STOCK_TCO2_HA,
    ):
        assert set(table) == keys


def test_every_evidence_cell_is_admissible():
    def cells():
        for biome, cats in rd.ESV_EVIDENCE.items():
            for cat, cs in cats.items():
                for c in cs:
                    yield biome, cat, c
        for half in rd._PERI_URBAN_MOSAIC:
            for cat, cs in half.items():
                for c in cs:
                    yield "peri_urban", cat, c

    for biome, cat, c in cells():
        assert c["n"] >= rd.MIN_VALUE_ESTIMATES, (biome, cat, c)
        assert c["source"] in rd.SOURCES
        assert c["service"] in rd.ESVD_2020_SERVICE_MEAN_MEDIAN
        assert c["value"] >= 0


def test_estimates_are_exactly_the_categories_without_evidence():
    for biome in rd.BIOMES:
        for cat in rd.ESV_CATEGORIES:
            if biome == "peri_urban":
                has_evidence = all(half[cat] for half in rd._PERI_URBAN_MOSAIC)
            else:
                has_evidence = bool(rd.ESV_EVIDENCE[biome][cat])
            assert has_evidence != ((biome, cat) in rd.ESV_ESTIMATES), (biome, cat)


def test_literature_values_are_reproducible_from_their_evidence():
    for biome in rd.BIOMES:
        for cat in rd.ESV_CATEGORIES:
            prov = rd.esv_provenance(biome, cat)
            assert prov["price_year"] == rd.PRICE_YEAR
            if prov["basis"] == "estimate":
                assert prov["evidence"] == []
                continue
            total = sum(e["usd_ha_yr"] for e in prov["evidence"])
            if biome == "peri_urban":
                total /= 2  # 50/50 mosaic
            assert abs(round(total) - rd.BIOMES[biome][f"{cat}_usd_ha_yr"]) <= 1, (biome, cat)


def test_sequestration_and_pools_carry_a_basis_and_source():
    for table in (rd.SEQUESTRATION, rd.BIOME_CARBON_POOLS):
        for biome, entry in table.items():
            assert entry["basis"] in ("literature", "estimate"), biome
            assert entry["source"], biome


def test_valuation_methodology_flags_estimates():
    res = compute_valuation(POLY_1HA_ISH, "tundra", "USD")
    m = res["methodology"]
    assert m["climate_regulation"]["basis"] == "estimate"
    assert m["soil_nutrient_value"]["basis"] == "literature"
    assert m["carbon_capture"]["sequestration_basis"] == "literature"
    for cat in rd.YIELD_CATEGORIES:
        assert m[cat]["price_year"] == rd.PRICE_YEAR


# --- unit conversions & invariants -------------------------------------------

def test_cpi_inflation_round_trips():
    for year in rd.CPI_U_ANNUAL_AVERAGE:
        x = 1234.5
        assert math.isclose(rd.inflate_usd(rd.inflate_usd(x, year), rd.PRICE_YEAR, year), x)
    # BLS CPI-U annual averages: 2007 -> 2024 is +51.3%.
    assert math.isclose(rd.inflate_usd(100, 2007), 151.29, abs_tol=0.01)


def test_per_sqm_round_trips_to_per_hectare():
    for biome, b in rd.BIOMES.items():
        per_sqm = rd.biome_per_sqm_usd(biome)
        for cat in rd.ESV_CATEGORIES:
            assert math.isclose(per_sqm[cat] * rd.SQM_PER_HECTARE, b[f"{cat}_usd_ha_yr"])
        assert math.isclose(
            per_sqm["carbon_capture"] * rd.SQM_PER_HECTARE,
            b["sequestration_tco2_ha_yr"] * rd.CARBON_PRICE_USD_PER_TCO2,
        )


def test_carbon_price_sits_in_the_ar6_2c_range_in_2024_dollars():
    # AR6 WGIII Ch. 3: 2 °C (>67%) pathways, 2030 MAC interquartile 60-120 USD2015.
    low = rd.inflate_usd(60, 2015)
    high = rd.inflate_usd(120, 2015)
    assert low <= rd.CARBON_PRICE_USD_PER_TCO2 <= high


def test_carbon_debt_bounds_and_intactness_scaling():
    for biome, pool in rd.BIOME_CARBON_POOLS.items():
        full = rd.biome_carbon_debt_tco2_ha(biome, 1.0)
        none = rd.biome_carbon_debt_tco2_ha(biome, 0.0)
        half = rd.biome_carbon_debt_tco2_ha(biome, 0.5)
        assert 0.0 <= pool["soil_release_fraction"] <= 1.0
        assert none <= half <= full <= rd.biome_carbon_stock_tco2_ha(biome) + 1e-9
        # Only vegetation scales with intactness: debt is linear in it.
        assert math.isclose(half, (full + none) / 2)
        assert math.isclose(none, pool["soil_tc_ha"] * pool["soil_release_fraction"] * rd.TCO2_PER_TC)


def test_srlulucf_densities():
    veg, soil = rd._srlulucf_density("Tropical forests")
    assert math.isclose(veg, 120.45, abs_tol=0.01)
    assert math.isclose(soil, 122.73, abs_tol=0.01)


def test_mangrove_pools_follow_ipcc_wetlands_supplement():
    pool = rd.BIOME_CARBON_POOLS["mangrove"]
    assert math.isclose(pool["vegetation_tc_ha"], 192 * 1.49 * 0.451, abs_tol=0.01)
    assert pool["soil_tc_ha"] == 386.0


def test_fx_rates_are_sane():
    assert rd.CURRENCIES["USD"]["rate_per_usd"] == 1.0
    assert 0.7 < rd.CURRENCIES["EUR"]["rate_per_usd"] < 1.1
    assert 3.0 < rd.CURRENCIES["BRL"]["rate_per_usd"] < 8.0


def test_currency_conversion_round_trips():
    usd = compute_valuation(POLY_1HA_ISH, "mangrove", "USD")
    for code in ("EUR", "BRL"):
        rate = rd.CURRENCIES[code]["rate_per_usd"]
        res = compute_valuation(POLY_1HA_ISH, "mangrove", code)
        assert math.isclose(res["total_ecosystem_value_per_year"] / rate,
                            usd["total_ecosystem_value_per_year"], rel_tol=1e-9)
        assert math.isclose(res["conversion_liability"]["carbon_debt_onetime"] / rate,
                            usd["conversion_liability"]["carbon_debt_onetime"], rel_tol=1e-9)
        # Comparisons are ranked on USD, so they must not depend on the currency.
        assert res["comparisons"] == usd["comparisons"]


@pytest.mark.parametrize("biome", sorted(PINNED))
def test_totals_equal_sum_of_services(biome):
    res = compute_valuation(POLY_1HA_ISH, biome, "USD", intactness=0.7)
    # Area totals are each rounded to cents.
    assert math.isclose(
        sum(res["yields_total_year"].values()),
        res["total_ecosystem_value_per_year"],
        abs_tol=0.05,
    )
    seq, climate, water, bio, soil = PINNED[biome]
    expected_per_sqm = (seq * rd.CARBON_PRICE_USD_PER_TCO2 + climate + water + bio + soil) / 1e4
    assert math.isclose(
        res["potential"]["total_ecosystem_value_per_sqm_year"], expected_per_sqm, abs_tol=1e-6
    )
    assert math.isclose(
        res["total_ecosystem_value_per_sqm_year"], expected_per_sqm * 0.7, abs_tol=1e-6
    )


def test_carbon_debt_in_valuation_scales_with_intactness():
    full = compute_valuation(POLY_1HA_ISH, "tropical_rainforest", "USD", intactness=1.0)
    half = compute_valuation(POLY_1HA_ISH, "tropical_rainforest", "USD", intactness=0.5)
    area_ha = full["area"]["sqm"] / rd.SQM_PER_HECTARE
    expected = rd.biome_carbon_debt_tco2_ha("tropical_rainforest", 1.0) * area_ha * 80.0
    assert math.isclose(full["conversion_liability"]["carbon_debt_onetime"], expected, rel_tol=1e-6)
    assert half["conversion_liability"]["carbon_debt_onetime"] < full["conversion_liability"]["carbon_debt_onetime"]


def test_data_hub_provenance_reflects_recalibration():
    from datasets import data_catalog

    domains = {d["id"]: d for d in data_catalog()["domains"]}
    esv = domains["esv_reference"]
    assert esv["as_of"] == "2024"
    assert any("Brander" in s["citation"] for s in esv["sources"])
    assert "flagged as unverified estimates" in esv["note"]
    carbon = domains["carbon_price"]
    assert "AR6" in carbon["sources"][0]["citation"]
    assert carbon["as_of"] == rd.CARBON_PRICE_AS_OF
    assert domains["fx_rates"]["as_of"] == rd.FX_AS_OF
