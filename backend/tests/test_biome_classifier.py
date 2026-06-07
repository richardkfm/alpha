"""Tests for the Phase 3 biome classifier (ingested boundary data).

Run from the backend/ directory:  python -m pytest
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biome_classifier import (  # noqa: E402
    classify_geometry,
    classify_point,
    representative_point,
)


def _polygon_around(lon, lat, d=0.5):
    return {
        "type": "Polygon",
        "coordinates": [
            [[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]
        ],
    }


def test_amazon_point_is_tropical_rainforest():
    res = classify_point(-62, -4)
    assert res["biome_key"] == "tropical_rainforest"
    assert res["confidence"] == "matched"
    assert res["matched_region"] == "Amazon Basin"


def test_great_plains_point_is_grassland():
    res = classify_point(-100, 42)
    assert res["biome_key"] == "temperate_grassland"
    assert res["confidence"] == "matched"


def test_sundarbans_point_is_mangrove():
    res = classify_point(89, 22)
    assert res["biome_key"] == "mangrove"


def test_open_ocean_falls_back_to_default():
    res = classify_point(-30, 0)  # mid-Atlantic, inside no boundary
    assert res["confidence"] == "default"
    assert res["biome_key"] == "tropical_rainforest"  # DEFAULT_BIOME
    assert res["matched_region"] is None


def test_classify_geometry_uses_representative_point():
    res = classify_geometry(_polygon_around(-62, -4))
    assert res["biome_key"] == "tropical_rainforest"


def test_representative_point_inside_simple_polygon():
    lon, lat = representative_point(_polygon_around(10, 20))
    assert abs(lon - 10) < 1e-9 and abs(lat - 20) < 1e-9


def test_feature_is_unwrapped():
    feature = {"type": "Feature", "geometry": _polygon_around(-62, -4)}
    assert classify_geometry(feature)["biome_key"] == "tropical_rainforest"


def test_empty_geometry_defaults():
    res = classify_geometry({})
    assert res["confidence"] == "default"
