"""alpha — region catalogue loader.

Loads the bundled ``data/regions.geojson`` catalogue of named ecosystems (across
all five valuation biomes) and values each one through the Phase 2 TEV engine.

This powers two frontend surfaces from a single API call:
  - the map overlays (one toggleable layer per biome), and
  - the Compare view (side-by-side Total Ecosystem Value breakdowns).

The geometries are coarse, illustrative footprints — not authoritative
boundaries. Each feature's ``biome_key`` is authoritative (it comes from the
dataset) so we value with it directly rather than re-classifying.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from reference_data import BIOMES, DEFAULT_BIOME, biome_default_intactness
from valuation import compute_valuation

_DATA_PATH = Path(__file__).parent / "data" / "regions.geojson"


@lru_cache(maxsize=1)
def _load_catalogue() -> Dict[str, Any]:
    """Read and cache the raw region FeatureCollection from disk."""
    with _DATA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def dataset_provenance() -> Dict[str, Any]:
    """Dataset name + source block, for client-side attribution."""
    fc = _load_catalogue()
    return {
        "name": fc.get("name", "alpha_regions"),
        "description": fc.get("description", ""),
        "source": fc.get("source", {}),
        "count": len(fc.get("features", [])),
    }


def list_regions(
    currency: str,
    carbon_price: float | None = None,
    fx_rate: float | None = None,
    fx_as_of: str | None = None,
    discount_rate: float | None = None,
) -> List[Dict[str, Any]]:
    """Value every catalogue region in ``currency`` and return flat summaries.

    Each region carries its geometry plus the fields the frontend needs to draw
    map overlays and the Compare breakdown, reusing ``compute_valuation`` so the
    numbers match the ``/api/v1/valuation`` endpoint exactly. ``carbon_price`` /
    ``fx_rate`` / ``fx_as_of`` are resolved once by the endpoint (live or static)
    and injected so the whole catalogue prices off one consistent snapshot.
    Realised value is scaled by each region's ``intactness`` (an explicit property
    or the biome default), and the annual flow is capitalised at ``discount_rate``.
    """
    regions: List[Dict[str, Any]] = []
    for feature in _load_catalogue().get("features", []):
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        biome_key = props.get("biome_key", DEFAULT_BIOME)
        if biome_key not in BIOMES:
            biome_key = DEFAULT_BIOME

        intactness = props.get("intactness")
        if intactness is None:
            intactness = biome_default_intactness(biome_key)

        valuation = compute_valuation(
            geometry,
            biome=biome_key,
            currency=currency,
            carbon_price=carbon_price,
            fx_rate=fx_rate,
            fx_as_of=fx_as_of,
            intactness=intactness,
            discount_rate=discount_rate,
        )
        regions.append(
            {
                "id": props.get("id"),
                "name": props.get("name"),
                "region": props.get("region"),
                "biome_key": valuation["biome_key"],
                "biome_label": valuation["biome"],
                "gdp_callout": props.get("gdp_callout"),
                "geometry": geometry,
                "area": valuation["area"],
                "currency": valuation["currency"],
                "currency_symbol": valuation["currency_symbol"],
                "intactness": valuation["intactness"],
                "yields_per_sqm_year": valuation["yields_per_sqm_year"],
                "total_ecosystem_value_per_sqm_year": valuation[
                    "total_ecosystem_value_per_sqm_year"
                ],
                "total_ecosystem_value_per_year": valuation[
                    "total_ecosystem_value_per_year"
                ],
                "potential": valuation["potential"],
                "capitalized_value": valuation["capitalized_value"],
            }
        )
    return regions
