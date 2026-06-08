"""alpha — Phase 3 biome classification from ingested boundary data.

Phase 2 accepted (or defaulted) the biome as an input. Phase 3 *ingests* real
biome-boundary data and classifies a geometry into one of alpha's five valuation
biomes by locating its representative point inside the ingested boundaries.

The primary boundaries live in ``data/ecoregions.geojson`` — real terrestrial
ecoregion boundaries (RESOLVE Ecoregions 2017, Dinerstein et al.), generalized and
mapped from the 14 RESOLVE biomes to alpha's valuation biomes. They are layered
with the curated ``data/wwf_biomes.geojson`` seeds, which cover the land-use and
freshwater types RESOLVE does not (cropland, peri-urban, lakes) and a few specific
sites; where boundaries overlap, the most specific (smallest bbox) wins. See
``backend/INGESTION.md`` for provenance and refresh.

Pure-Python and dependency-free (ray-casting point-in-polygon), matching the
valuation engine's design. When a point falls inside no ingested boundary, the
classifier returns the configured default biome with ``confidence: "default"`` so
the valuation endpoint can still respond.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Optional

from reference_data import BIOMES, DEFAULT_BIOME

# The ingested boundary datasets ship with the backend. The real RESOLVE
# ecoregions are the primary source; the curated seeds add the land-use /
# freshwater types RESOLVE lacks and a few specific sites.
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ECOREGIONS_PATH = os.path.join(_DATA_DIR, "ecoregions.geojson")
SEEDS_PATH = os.path.join(_DATA_DIR, "wwf_biomes.geojson")
# Ordered so the real ecoregions load first; seeds layer on top (smaller bbox
# seeds still win via the specificity ranking in classify_point).
DATA_PATHS = [ECOREGIONS_PATH, SEEDS_PATH]


def _iter_polygons(geometry: dict[str, Any]):
    """Yield each ``[ [ring], ... ]`` polygon from a Polygon/MultiPolygon."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return
    if gtype == "Polygon":
        yield coords
    elif gtype == "MultiPolygon":
        for poly in coords:
            yield poly


def _bbox(rings: list[list[list[float]]]) -> tuple[float, float, float, float]:
    """Bounding box (min_lon, min_lat, max_lon, max_lat) of a polygon's exterior."""
    ext = rings[0]
    lons = [p[0] for p in ext]
    lats = [p[1] for p in ext]
    return min(lons), min(lats), max(lons), max(lats)


def _bbox_area(rings: list[list[list[float]]]) -> float:
    """Cheap planar bbox area (deg²) — used only to rank specificity, not to value."""
    min_lon, min_lat, max_lon, max_lat = _bbox(rings)
    return (max_lon - min_lon) * (max_lat - min_lat)


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test for a single linear ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersects = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _point_in_polygon(lon: float, lat: float, rings: list[list[list[float]]]) -> bool:
    """Point is inside the exterior ring and outside every hole."""
    if not rings or not _point_in_ring(lon, lat, rings[0]):
        return False
    for hole in rings[1:]:
        if _point_in_ring(lon, lat, hole):
            return False
    return True


def representative_point(geometry: dict[str, Any]) -> Optional[tuple[float, float]]:
    """A representative interior-ish point (lon, lat) for a GeoJSON geometry.

    Uses the centroid of the largest member polygon's exterior vertices. For the
    coarse footprints alpha works with this reliably lands inside the polygon; it
    is only used to *locate* the geometry against biome boundaries, never to value
    it (area still uses the exact geodesic computation in ``valuation.py``).
    """
    if not isinstance(geometry, dict):
        return None
    if geometry.get("type") == "Feature":
        geometry = geometry.get("geometry") or {}

    largest: Optional[list[list[list[float]]]] = None
    largest_area = -1.0
    for poly in _iter_polygons(geometry):
        if not poly:
            continue
        area = _bbox_area(poly)
        if area > largest_area:
            largest_area, largest = area, poly

    if not largest:
        return None
    ext = largest[0]
    # Drop the closing vertex (== first) so it doesn't bias the centroid.
    if len(ext) > 1 and ext[0] == ext[-1]:
        ext = ext[:-1]
    lon = sum(p[0] for p in ext) / len(ext)
    lat = sum(p[1] for p in ext) / len(ext)
    return lon, lat


@lru_cache(maxsize=1)
def _load_boundaries() -> list[dict[str, Any]]:
    """Load and pre-process the ingested biome boundaries (cached).

    Returns a list of ``{biome_key, name, wwf_biome, polygon, specificity}`` where
    ``polygon`` is the raw ring list and ``specificity`` is the bbox area used to
    prefer smaller, more specific biomes (e.g. a mangrove patch inside a wider
    tropical region) when boundaries overlap.
    """
    boundaries: list[dict[str, Any]] = []
    for path in DATA_PATHS:
        if not os.path.exists(path):
            continue
        # Curated seeds take priority over the real ecoregions: they intentionally
        # override RESOLVE for the land-use / freshwater types it lacks (a lake or
        # farmland sits on a "forest" ecoregion) and for a few specific sites.
        is_seed = os.path.basename(path) == os.path.basename(SEEDS_PATH)
        with open(path, "r", encoding="utf-8") as fh:
            fc = json.load(fh)
        for feat in fc.get("features", []):
            props = feat.get("properties", {})
            biome_key = props.get("biome_key")
            if biome_key not in BIOMES:
                continue
            for poly in _iter_polygons(feat.get("geometry", {})):
                if not poly:
                    continue
                boundaries.append(
                    {
                        "biome_key": biome_key,
                        "name": props.get("name", ""),
                        "wwf_biome": props.get("wwf_biome", ""),
                        "polygon": poly,
                        "specificity": _bbox_area(poly),
                        "priority": 1 if is_seed else 0,
                    }
                )
    return boundaries


def boundary_source() -> dict[str, Any]:
    """The provenance block from the ingested datasets (for API transparency)."""
    src: dict[str, Any] = {}
    if os.path.exists(ECOREGIONS_PATH):
        with open(ECOREGIONS_PATH, "r", encoding="utf-8") as fh:
            src = dict(json.load(fh).get("source", {}))
    src.setdefault(
        "seeds",
        "Curated seeds (data/wwf_biomes.geojson) supply land-use/freshwater types "
        "RESOLVE omits (cropland, peri-urban, lakes).",
    )
    return src


def classify_point(lon: float, lat: float) -> dict[str, Any]:
    """Classify a single coordinate into a valuation biome.

    Returns the matched biome plus metadata. When the point lies inside several
    boundaries, the most specific (smallest bbox) wins. When it lies inside none,
    the default biome is returned with ``confidence: "default"``.
    """
    matches = [
        b for b in _load_boundaries() if _point_in_polygon(lon, lat, b["polygon"])
    ]
    if matches:
        # Prefer a curated seed (priority) over an ecoregion; then the most
        # specific (smallest bbox) among equal priority.
        best = min(matches, key=lambda b: (-b["priority"], b["specificity"]))
        return {
            "biome_key": best["biome_key"],
            "biome_label": BIOMES[best["biome_key"]]["label"],
            "matched_region": best["name"],
            "wwf_biome": best["wwf_biome"],
            "point": {"lon": round(lon, 5), "lat": round(lat, 5)},
            "confidence": "matched",
            "source": "RESOLVE Ecoregions 2017 (Dinerstein et al.), generalized; curated seeds for land-use/freshwater types",
        }
    return {
        "biome_key": DEFAULT_BIOME,
        "biome_label": BIOMES[DEFAULT_BIOME]["label"],
        "matched_region": None,
        "wwf_biome": None,
        "point": {"lon": round(lon, 5), "lat": round(lat, 5)},
        "confidence": "default",
        "source": "no boundary match — fell back to default biome",
    }


def classify_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    """Classify a GeoJSON Polygon/MultiPolygon/Feature into a valuation biome."""
    point = representative_point(geometry)
    if point is None:
        return {
            "biome_key": DEFAULT_BIOME,
            "biome_label": BIOMES[DEFAULT_BIOME]["label"],
            "matched_region": None,
            "wwf_biome": None,
            "point": None,
            "confidence": "default",
            "source": "no usable geometry — fell back to default biome",
        }
    return classify_point(point[0], point[1])
