"""alpha — Phase 2 Total Ecosystem Value (TEV) engine.

Pure-Python, dependency-free valuation: compute the geodesic area of a GeoJSON
polygon, look up biome reference yields, scale by area, and convert to the
requested currency. Every formula is documented here and in
`backend/METHODOLOGY.md`, with citations in `reference_data.py`.
"""
from __future__ import annotations

import math
from typing import Any

from reference_data import (
    BIOMES,
    CARBON_PRICE_USD_PER_TCO2,
    CURRENCIES,
    DEFAULT_BIOME,
    DEFAULT_CURRENCY,
    DEFAULT_DISCOUNT_RATE,
    FX_AS_OF,
    YIELD_CATEGORIES,
    biome_carbon_stock_tco2_ha,
    biome_per_sqm_usd,
    biome_red_lines,
    biome_scarcity_weight,
)

# Mean Earth radius (metres), IUGG. Used for the spherical-excess area formula.
EARTH_RADIUS_M = 6_371_008.8


def _ring_area_sqm(ring: list[list[float]]) -> float:
    """Signed geodesic area (m^2) of one linear ring of [lon, lat] degrees.

    Spherical-excess formula (Chamberlain & Duquette, JPL; the same algorithm
    used by OpenLayers / Google Maps geometry). Sign encodes winding order, so
    callers take the absolute value for exterior rings and use the magnitude to
    subtract holes.
    """
    n = len(ring)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        lon1, lat1 = ring[i][0], ring[i][1]
        lon2, lat2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        total += math.radians(lon2 - lon1) * (
            2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )
    return total * EARTH_RADIUS_M * EARTH_RADIUS_M / 2.0


def _polygon_area_sqm(rings: list[list[list[float]]]) -> float:
    """Area (m^2) of a GeoJSON Polygon: exterior ring minus any holes."""
    if not rings:
        return 0.0
    exterior = abs(_ring_area_sqm(rings[0]))
    holes = sum(abs(_ring_area_sqm(r)) for r in rings[1:])
    return max(exterior - holes, 0.0)


def geodesic_area_sqm(geometry: dict[str, Any]) -> float:
    """Area in square metres of a GeoJSON Polygon or MultiPolygon geometry.

    Accepts a bare geometry or a Feature (unwraps ``geometry``). Returns 0.0 for
    geometries with no usable polygonal coordinates rather than raising, so the
    endpoint can surface a friendly validation error instead.
    """
    if not isinstance(geometry, dict):
        return 0.0
    if geometry.get("type") == "Feature":
        geometry = geometry.get("geometry") or {}

    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return 0.0

    if gtype == "Polygon":
        return _polygon_area_sqm(coords)
    if gtype == "MultiPolygon":
        return sum(_polygon_area_sqm(poly) for poly in coords)
    return 0.0


def _round_money(value: float) -> float:
    """Round currency totals to cents."""
    return round(value, 2)


def _round_per_sqm(value: float) -> float:
    """Per-sqm yields are sub-cent; keep 6 significant decimals."""
    return round(value, 6)


def compute_valuation(
    geometry: dict[str, Any],
    biome: str = DEFAULT_BIOME,
    currency: str = DEFAULT_CURRENCY,
    carbon_price: float | None = None,
    fx_rate: float | None = None,
    fx_as_of: str | None = None,
    intactness: float = 1.0,
    discount_rate: float | None = None,
) -> dict[str, Any]:
    """Compute the full TEV breakdown for a polygon.

    Steps:
      1. area_sqm = geodesic area of the polygon.
      2. per-sqm reference yields for the biome (USD), converted to `currency`.
      3. scale by ``intactness`` (the share of reference yield the land actually
         delivers given its current land cover); report the intact ceiling too.
      4. total annual yields = realised per-sqm * area_sqm.
      5. TEV = sum of the five categories (per sqm, and total for the area).
      6. capitalise the annual flow into a present-value "standing asset"
         (annual / discount_rate).

    ``carbon_price``, ``fx_rate`` and ``fx_as_of`` default to the documented
    static references; the API layer injects live values when Phase 4 market data
    is enabled (see ``live_data.py``). ``intactness`` defaults to 1.0 and
    ``discount_rate`` to the documented reference, so passing nothing reproduces
    the Phase 2 static behaviour exactly.
    """
    biome_key = biome if biome in BIOMES else DEFAULT_BIOME
    currency = currency.upper()
    if currency not in CURRENCIES:
        currency = DEFAULT_CURRENCY
    fx = CURRENCIES[currency]
    rate = fx["rate_per_usd"] if fx_rate is None else fx_rate
    as_of = FX_AS_OF if fx_as_of is None else fx_as_of
    carbon_price = CARBON_PRICE_USD_PER_TCO2 if carbon_price is None else carbon_price
    intactness = min(max(intactness, 0.0), 1.0)
    discount_rate = DEFAULT_DISCOUNT_RATE if discount_rate is None else discount_rate

    area_sqm = geodesic_area_sqm(geometry)

    base_usd = biome_per_sqm_usd(biome_key, carbon_price=carbon_price)  # USD per sqm per year
    b = BIOMES[biome_key]

    yields_per_sqm: dict[str, float] = {}
    yields_total: dict[str, float] = {}
    for cat in YIELD_CATEGORIES:
        per_sqm_cur = base_usd[cat] * rate * intactness  # realised (intactness-scaled)
        yields_per_sqm[cat] = _round_per_sqm(per_sqm_cur)
        yields_total[cat] = _round_money(per_sqm_cur * area_sqm)

    tev_per_sqm_intact = sum(base_usd[c] for c in YIELD_CATEGORIES) * rate  # full potential
    tev_per_sqm = tev_per_sqm_intact * intactness  # realised
    tev_total = tev_per_sqm * area_sqm
    tev_total_intact = tev_per_sqm_intact * area_sqm

    # Capitalise the realised annual flow into a present-value standing asset.
    asset_per_sqm = tev_per_sqm / discount_rate if discount_rate else 0.0
    asset_total = tev_total / discount_rate if discount_rate else 0.0

    # --- Systemic / conversion layer (the "cost of conversion" reframing) -----
    # A parcel's loss carries the weight of the wider system: rare + intact land
    # is load-bearing, so it earns a systemic premium (>=1). This is NOT a price
    # to outbid — it frames conversion as a perpetual liability owed to others.
    scarcity = biome_scarcity_weight(biome_key)
    systemic_multiplier = 1.0 + scarcity * intactness
    systemic_per_sqm = tev_per_sqm * systemic_multiplier
    systemic_asset_total = asset_total * systemic_multiplier

    # One-time, largely irreversible carbon debt of clearing the standing stock.
    area_ha = area_sqm / 10_000.0
    carbon_debt_onetime = (
        biome_carbon_stock_tco2_ha(biome_key) * area_ha * carbon_price * rate
    )

    red_lines = biome_red_lines(biome_key)

    methodology = {
        "carbon_capture": {
            "formula": "sequestration (tCO2/ha/yr) x carbon price (USD/tCO2) / 10000",
            "sequestration_tco2_ha_yr": b["sequestration_tco2_ha_yr"],
            "carbon_price_usd_per_tco2": round(carbon_price, 4),
            "citation": "Pan et al. 2011; IPCC AR6 WGIII (2022)",
        },
        "climate_regulation": {
            "formula": "ESVD climate-regulation reference (USD/ha/yr) / 10000",
            "reference_usd_ha_yr": b["climate_regulation_usd_ha_yr"],
            "citation": "de Groot et al. 2012; Costanza et al. 2014",
        },
        "water_filtration": {
            "formula": "ESVD water purification + flow regulation (USD/ha/yr) / 10000",
            "reference_usd_ha_yr": b["water_filtration_usd_ha_yr"],
            "citation": "de Groot et al. 2012 (ESVD)",
        },
        "biodiversity_premium": {
            "formula": "ESVD genetic resources + habitat/refugia (USD/ha/yr) / 10000",
            "reference_usd_ha_yr": b["biodiversity_premium_usd_ha_yr"],
            "citation": "de Groot et al. 2012 (ESVD)",
        },
        "soil_nutrient_value": {
            "formula": "ESVD erosion prevention + soil fertility (USD/ha/yr) / 10000",
            "reference_usd_ha_yr": b["soil_nutrient_value_usd_ha_yr"],
            "citation": "de Groot et al. 2012 (ESVD)",
        },
    }

    return {
        "biome": b["label"],
        "biome_key": biome_key,
        "currency": currency,
        "currency_symbol": fx["symbol"],
        "area": {
            "sqm": round(area_sqm, 2),
            "hectares": round(area_sqm / 10_000.0, 4),
        },
        "yields_per_sqm_year": yields_per_sqm,
        "yields_total_year": yields_total,
        "total_ecosystem_value_per_sqm_year": _round_per_sqm(tev_per_sqm),
        "total_ecosystem_value_per_year": _round_money(tev_total),
        "intactness": round(intactness, 3),
        "potential": {
            "total_ecosystem_value_per_sqm_year": _round_per_sqm(tev_per_sqm_intact),
            "total_ecosystem_value_per_year": _round_money(tev_total_intact),
        },
        "capitalized_value": {
            "discount_rate": discount_rate,
            "asset_value_per_sqm": _round_per_sqm(asset_per_sqm),
            "asset_value_total": _round_money(asset_total),
        },
        "systemic": {
            "scarcity_weight": round(scarcity, 3),
            "multiplier": round(systemic_multiplier, 3),
            "value_per_sqm_year": _round_per_sqm(systemic_per_sqm),
            "rationale": (
                "Rare, intact systems are load-bearing; their loss degrades the wider "
                "network beyond the parcel itself. Premium = 1 + scarcity x intactness."
            ),
        },
        # Conversion reframed as a permanent, externalised liability — deliberately
        # not a figure to net against development revenue.
        "conversion_liability": {
            "annual_loss": _round_money(tev_total),
            "present_value": _round_money(systemic_asset_total),
            "carbon_debt_onetime": _round_money(carbon_debt_onetime),
            "incidence": (
                "Borne by the public, downstream communities and future generations — "
                "not captured by whoever converts the land."
            ),
            "note": "A debt owed to others in perpetuity, not a price the project can buy out.",
        },
        "red_lines": red_lines,
        "fx": {"base": "USD", "rate_per_usd": rate, "as_of": as_of},
        "methodology": methodology,
        "methodology_note": (
            "Phase 2 valuation engine. Per-biome reference values from the ESVD "
            "(de Groot et al. 2012) and carbon sequestration from Pan et al. 2011, "
            "priced via an IPCC-AR6-consistent reference carbon price. FX rates are "
            "indicative (as of {as_of}). See backend/METHODOLOGY.md.".format(as_of=FX_AS_OF)
        ),
    }
