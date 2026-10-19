"""Polygons crossing the antimeridian (180th meridian).

GeoJSON clients commonly write such a ring with longitudes that jump sign
(177 .. -178) rather than splitting it. The area and the classifier must take
each edge the short way round instead of the 358-degree planar way.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from biome_classifier import classify_geometry, representative_point  # noqa: E402
from main import app  # noqa: E402
from valuation import EARTH_RADIUS_M, geodesic_area_sqm  # noqa: E402

client = TestClient(app)

# Fiji-sized box, 178E .. 179W, written with sign-jumping longitudes ...
CROSSING = {
    "type": "Polygon",
    "coordinates": [[[178, -19], [-179, -19], [-179, -16], [178, -16], [178, -19]]],
}
# ... and the same box written with continuous longitudes (178 .. 181).
CONTINUOUS = {
    "type": "Polygon",
    "coordinates": [[[178, -19], [181, -19], [181, -16], [178, -16], [178, -19]]],
}
# Chukotka tundra, 170E .. 176W.
CHUKOTKA = {
    "type": "Polygon",
    "coordinates": [[[170, 65], [-176, 65], [-176, 67], [170, 67], [170, 65]]],
}


def test_crossing_ring_area_matches_the_continuous_form():
    crossing = geodesic_area_sqm(CROSSING)
    assert math.isclose(crossing, geodesic_area_sqm(CONTINUOUS), rel_tol=1e-9)
    # ~3 x 3 degrees near 17.5S: about 1e11 m^2, not a band around the planet.
    assert 0.9e11 < crossing < 1.2e11


def test_polar_cap_ring_with_a_full_360_seam_is_unchanged():
    cap = {
        "type": "Polygon",
        "coordinates": [[[-180, -60], [180, -60], [180, -90], [-180, -90], [-180, -60]]],
    }
    expected = 2 * math.pi * EARTH_RADIUS_M**2 * (1 - math.sin(math.radians(60)))
    assert math.isclose(geodesic_area_sqm(cap), expected, rel_tol=1e-9)


def test_representative_point_of_a_crossing_ring_is_near_the_antimeridian():
    lon, lat = representative_point(CHUKOTKA)
    assert math.isclose(lon, 177.0, abs_tol=1e-9)
    assert math.isclose(lat, 66.0, abs_tol=1e-9)
    lon, _ = representative_point(CROSSING)
    assert abs(abs(lon) - 180) < 1.0  # 179.5E, not 0.5W in the Gulf of Guinea


def test_crossing_polygon_is_classified_where_it_actually_is():
    assert classify_geometry(CHUKOTKA)["biome_key"] == "tundra"


def test_valuation_endpoint_values_a_crossing_polygon_sensibly():
    a = client.post("/api/v1/valuation", json=CROSSING, params={"biome": "mangrove"}).json()
    b = client.post("/api/v1/valuation", json=CONTINUOUS, params={"biome": "mangrove"}).json()
    assert a["area"] == b["area"]
    assert a["total_ecosystem_value_per_year"] == b["total_ecosystem_value_per_year"]
