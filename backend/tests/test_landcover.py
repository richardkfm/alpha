"""Tests for the Phase 3 Copernicus land-cover legend/intactness layer."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from landcover import (  # noqa: E402
    DEFAULT_INTACTNESS,
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
    assert dominant_biome_hint({40: 0.9, 112: 0.1}) is None  # cropland has no hint
