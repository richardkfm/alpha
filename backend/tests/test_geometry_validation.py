"""Malformed GeoJSON must be rejected with a 422, never escape as a 500."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

SQUARE = [[-65, -5], [-60, -5], [-60, -2], [-65, -2], [-65, -5]]

MALFORMED = {
    "empty ring": {"type": "Polygon", "coordinates": [[]]},
    "ring of bare numbers": {"type": "Polygon", "coordinates": [[1, 2, 3]]},
    "string positions": {
        "type": "Polygon",
        "coordinates": [[["a", "b"], ["c", "d"], ["e", "f"], ["a", "b"]]],
    },
    "one-number positions": {"type": "Polygon", "coordinates": [[[1], [2], [3], [1]]]},
    "boolean positions": {
        "type": "Polygon",
        "coordinates": [[[True, False], [True, True], [False, True], [True, False]]],
    },
    "multipolygon with an empty member": {
        "type": "MultiPolygon",
        "coordinates": [[SQUARE], [[]]],
    },
    "multipolygon coordinates not an array": {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": "nope"},
    },
    "latitude out of range": {
        "type": "Polygon",
        "coordinates": [[[0, 0], [10, 0], [10, 200], [0, 200], [0, 0]]],
    },
}


@pytest.mark.parametrize("path", ["/api/v1/valuation", "/api/v1/classify", "/api/v1/valuation/export"])
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_geometry_is_a_422(path, name):
    res = client.post(path, json=MALFORMED[name])
    assert res.status_code == 422, (name, res.status_code, res.text[:200])
    assert "detail" in res.json()


@pytest.mark.parametrize("path", ["/api/v1/valuation", "/api/v1/classify"])
def test_nan_coordinates_are_a_422(path):
    # Python's json module (and so FastAPI) accepts the non-standard NaN literal.
    body = '{"type":"Polygon","coordinates":[[[NaN,0],[1,0],[1,1],[0,1],[NaN,0]]]}'
    res = client.post(path, content=body, headers={"Content-Type": "application/json"})
    assert res.status_code == 422


def test_valid_polygon_and_multipolygon_still_value():
    poly = {"type": "Polygon", "coordinates": [SQUARE]}
    multi = {"type": "MultiPolygon", "coordinates": [[SQUARE]]}
    for geom in (poly, multi, {"type": "Feature", "properties": {}, "geometry": poly}):
        res = client.post("/api/v1/valuation", json=geom)
        assert res.status_code == 200
        assert res.json()["area"]["sqm"] > 0


def test_unclosed_three_point_ring_is_still_accepted():
    # Lenient clients send unclosed rings; the area maths closes them implicitly.
    tri = {"type": "Polygon", "coordinates": [[[-65, -5], [-60, -5], [-60, -2]]]}
    assert client.post("/api/v1/valuation", json=tri).status_code == 200
