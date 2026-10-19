"""alpha — Phase 3 Copernicus land-cover ingestion layer.

The biome classifier (``biome_classifier.py``) answers *which biome* a polygon
belongs to. Copernicus land cover answers *what is actually on the ground there
now* — intact forest, cropland, urban — which scales the realised ecosystem
value: a "tropical rainforest" polygon that has been cleared to cropland no longer
delivers the intact-forest yield.

This module ships the authoritative legend of the **Copernicus Global Land Service
Dynamic Land Cover (CGLS-LC100, 100 m, collection 3)** discrete classification and
maps each class to:

  - a biome *hint* (cross-checks / overrides the boundary classifier where the
    boundaries are coarse), and
  - an **intactness factor** in [0, 1] — the fraction of the biome's reference
    ecosystem yield a parcel in that land-cover class is assumed to still deliver.

Real raster lookups (sampling the CGLS-LC100 GeoTIFF for a polygon) are an
infrastructure concern handled by the ingestion pipeline / PostGIS in deployment;
this module is the pure-Python legend + scoring those lookups feed into, so the
mapping is unit-testable offline. See ``backend/INGESTION.md``.

Source: Buchhorn, M. et al. (2020). *Copernicus Global Land Service: Land Cover
100m: collection 3.* Zenodo. https://doi.org/10.5281/zenodo.3939050
"""
from __future__ import annotations

from typing import Any, Optional

# CGLS-LC100 discrete-classification legend.
#   code -> (label, biome_hint or None, intactness_factor in [0, 1])
# intactness_factor is the share of intact-biome reference yield assumed to remain
# for that cover class *when the class is not the biome's own natural cover*
# (see ``NATURAL_COVER``). Natural/closed classes ~1.0; degraded/managed lower;
# built / bare ~0. These factors are heuristic judgements, not literature-derived
# values. biome_hint is set only where the cover class strongly implies one of
# alpha's valuation biomes. Evergreen needleleaf forest (111/121) spans both the
# temperate and boreal zones and keeps the temperate hint; deciduous needleleaf
# forest (113/123) is overwhelmingly boreal larch.
LC100_LEGEND: dict[int, tuple[str, Optional[str], float]] = {
    0:   ("Unknown / no input data", None, 0.0),
    20:  ("Shrubs", None, 0.55),
    30:  ("Herbaceous vegetation", "temperate_grassland", 0.6),
    40:  ("Cultivated / managed cropland", "cropland", 0.1),
    50:  ("Urban / built-up", None, 0.0),
    60:  ("Bare / sparse vegetation", "desert", 0.05),
    70:  ("Snow and ice", None, 0.0),
    80:  ("Permanent water bodies", "freshwater", 0.3),
    90:  ("Herbaceous wetland", "wetland", 0.95),
    100: ("Moss and lichen", "tundra", 0.3),
    111: ("Closed forest, evergreen needleleaf", "temperate_forest", 1.0),
    112: ("Closed forest, evergreen broadleaf", "tropical_rainforest", 1.0),
    113: ("Closed forest, deciduous needleleaf", "boreal_forest", 0.95),
    114: ("Closed forest, deciduous broadleaf", "temperate_forest", 0.95),
    115: ("Closed forest, mixed", "temperate_forest", 0.95),
    116: ("Closed forest, other / unknown", None, 0.9),
    121: ("Open forest, evergreen needleleaf", "temperate_forest", 0.75),
    122: ("Open forest, evergreen broadleaf", "tropical_rainforest", 0.75),
    123: ("Open forest, deciduous needleleaf", "boreal_forest", 0.7),
    124: ("Open forest, deciduous broadleaf", "temperate_forest", 0.7),
    125: ("Open forest, mixed", "temperate_forest", 0.7),
    126: ("Open forest, other / unknown", None, 0.65),
    200: ("Open sea", None, 0.0),
}

# Mangroves are a thematic overlay in the Copernicus product rather than a discrete
# class code; deployments cross-reference the Global Mangrove Watch layer. We model
# it here so the legend covers the mangrove valuation biome.
MANGROVE_PSEUDO_CODE = 99
LC100_LEGEND[MANGROVE_PSEUDO_CODE] = ("Mangrove (GMW overlay)", "mangrove", 1.0)

# Cover classes that *are* the intact state of a biome: open desert is bare /
# sparse vegetation and shrubs; intact tundra is moss, lichen, dwarf shrub, herbs
# and snow; a lake is open water. Scored against those biomes, such classes are
# fully intact (1.0) rather than degraded land, which is what their generic
# factor assumes. Applied only when the caller names the biome being scored.
NATURAL_COVER: dict[str, frozenset[int]] = {
    "desert": frozenset({20, 30, 60}),
    "tundra": frozenset({20, 30, 70, 100}),
    "freshwater": frozenset({80, 90}),
    "wetland": frozenset({80, 90}),
    "temperate_grassland": frozenset({20, 30}),
    "cropland": frozenset({40}),
    "mangrove": frozenset({MANGROVE_PSEUDO_CODE, 80}),
}

DEFAULT_INTACTNESS = 0.5


def land_cover_profile(code: int) -> dict[str, Any]:
    """Return ``{code, label, biome_hint, intactness_factor, known}`` for a class.

    Unknown codes fall back to a neutral mid intactness so a missing/partial
    raster reading never zeroes out a valuation silently.
    """
    entry = LC100_LEGEND.get(code)
    if entry is None:
        return {
            "code": code,
            "label": "Unrecognised land-cover class",
            "biome_hint": None,
            "intactness_factor": DEFAULT_INTACTNESS,
            "known": False,
        }
    label, biome_hint, intactness = entry
    return {
        "code": code,
        "label": label,
        "biome_hint": biome_hint,
        "intactness_factor": intactness,
        "known": True,
    }


def intactness_factor(code: int, biome_key: Optional[str] = None) -> float:
    """Intactness of one cover class, optionally relative to a specific biome.

    When ``biome_key`` is given and the class is part of that biome's natural
    cover (``NATURAL_COVER``), the class is fully intact (1.0); otherwise the
    class's generic factor applies.
    """
    if biome_key is not None and code in NATURAL_COVER.get(biome_key, frozenset()):
        return 1.0
    return land_cover_profile(code)["intactness_factor"]


def aggregate_intactness(
    class_fractions: dict[int, float], biome_key: Optional[str] = None
) -> float:
    """Area-weighted intactness for a polygon given its land-cover class mix.

    ``class_fractions`` maps LC100 codes to the fraction of the polygon's area in
    that class (as a real raster sample would yield). Fractions are normalised, so
    they need not sum to exactly 1. ``biome_key`` (optional) is the biome the
    polygon is valued as, so that biome's own natural cover is not scored as
    degraded. Returns a factor in [0, 1] that callers can multiply against the
    intact-biome reference yield.
    """
    total = sum(f for f in class_fractions.values() if f > 0)
    if total <= 0:
        return DEFAULT_INTACTNESS
    weighted = sum(
        intactness_factor(code, biome_key) * max(frac, 0.0)
        for code, frac in class_fractions.items()
    )
    return round(weighted / total, 4)


def dominant_biome_hint(class_fractions: dict[int, float]) -> Optional[str]:
    """The biome implied by the largest-area land-cover class, if any."""
    best_code: Optional[int] = None
    best_frac = 0.0
    for code, frac in class_fractions.items():
        if frac > best_frac:
            best_frac, best_code = frac, code
    if best_code is None:
        return None
    return land_cover_profile(best_code)["biome_hint"]
