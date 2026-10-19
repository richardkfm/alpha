"""Tests for the Phase 3 Copernicus land-cover legend/intactness layer."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from landcover import (  # noqa: E402
    DEFAULT_INTACTNESS,
    LC100_LEGEND,
    NATURAL_COVER,
    aggregate_intactness,
    dominant_biome_hint,
    land_cover_profile,
)


def test_closed_broadleaf_is_intact_rainforest():
    p = land_cover_profile(112)
    assert p["biome_hint"] == "tropical_rainforest"
    assert p["intactness_factor"] == 1.0
    assert p["known"] is True


def test_cropland_intactness_is_low():
    assert land_cover_profile(40)["intactness_factor"] <= 0.2


def test_urban_intactness_is_zero():
    assert land_cover_profile(50)["intactness_factor"] == 0.0


def test_unknown_code_returns_neutral_default():
    p = land_cover_profile(7777)
    assert p["known"] is False
    assert p["intactness_factor"] == DEFAULT_INTACTNESS


def test_aggregate_intactness_area_weighted():
    # Half intact closed broadleaf forest (1.0), half cropland (0.1) -> ~0.55.
    score = aggregate_intactness({112: 0.5, 40: 0.5})
    assert abs(score - 0.55) < 1e-6


def test_aggregate_normalises_unnormalised_fractions():
    # Fractions need not sum to 1; weighting still works.
    score = aggregate_intactness({112: 2.0, 40: 2.0})
    assert abs(score - 0.55) < 1e-6


def test_aggregate_empty_returns_default():
    assert aggregate_intactness({}) == DEFAULT_INTACTNESS


def test_dominant_biome_hint_picks_largest_class():
    assert dominant_biome_hint({112: 0.7, 40: 0.3}) == "tropical_rainforest"
    assert dominant_biome_hint({40: 0.9, 112: 0.1}) == "cropland"
    assert dominant_biome_hint({50: 0.9, 112: 0.1}) is None  # built-up has no hint


def test_every_biome_hint_is_a_valuation_biome():
    from reference_data import BIOMES

    hints = {land_cover_profile(c)["biome_hint"] for c in LC100_LEGEND} - {None}
    assert hints <= set(BIOMES)
    # The biomes added after the legend was first written are reachable too.
    assert {"cropland", "freshwater", "tundra", "desert", "boreal_forest"} <= hints
    assert set(NATURAL_COVER) <= set(BIOMES)


def test_natural_cover_is_intact_for_its_own_biome():
    # Open desert is bare/sparse vegetation: degraded for a forest, intact for a desert.
    assert aggregate_intactness({60: 1.0}) == 0.05
    assert aggregate_intactness({60: 1.0}, biome_key="desert") == 1.0
    assert aggregate_intactness({100: 1.0}, biome_key="tundra") == 1.0
    assert aggregate_intactness({80: 1.0}, biome_key="freshwater") == 1.0
    # Cropland cover inside a rainforest is still degraded.
    assert aggregate_intactness({40: 1.0}, biome_key="tropical_rainforest") == 0.1
    # Mixed: half intact desert, half urban.
    assert aggregate_intactness({60: 0.5, 50: 0.5}, biome_key="desert") == 0.5
