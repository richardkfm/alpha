"""alpha — data catalogue / provenance for the Data Hub.

Assembles, from the values that already live across the backend, a structured
catalogue of every data domain the valuation rests on — its source, citation,
"as-of" date, and a real-vs-placeholder status — plus a forward-looking
"data we still need" roadmap. The GUI Data Hub renders this verbatim so the
provenance shown to users is generated from the same constants the engine uses,
not a separate hand-maintained list.

Nothing here computes valuations; it only describes the inputs.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from biome_classifier import boundary_source
from live_data import get_carbon_price, get_fx_rates
from reference_data import (
    BIOMES,
    CARBON_PRICE_AS_OF,
    CARBON_PRICE_SOURCE,
    CARBON_PRICE_USD_PER_TCO2,
    CURRENCIES,
    ESV_CATEGORIES,
    ESV_ESTIMATES,
    FX_AS_OF,
    FX_SOURCE,
    PRICE_YEAR,
    SEQUESTRATION,
)
from regions import dataset_provenance
from scale_anchors import anchor_provenance

# Status vocabulary surfaced as colour-coded badges in the GUI:
#   authoritative — real, survey/peer-reviewed data used as-is
#   reference     — peer-reviewed reference values, static (not live)
#   placeholder   — illustrative / coarse / indicative stand-in pending real data
_AUTHORITATIVE = "authoritative"
_REFERENCE = "reference"
_PLACEHOLDER = "placeholder"

_LC100_CITATION = (
    "Buchhorn, M. et al. (2020). Copernicus Global Land Service: Land Cover 100m, "
    "collection 3. Zenodo. https://doi.org/10.5281/zenodo.3939050"
)


def _carbon_domain() -> Dict[str, Any]:
    price, meta = get_carbon_price()
    live = meta.get("live", False)
    return {
        "id": "carbon_price",
        "label": "Carbon price",
        "category": "valuation",
        "status": _AUTHORITATIVE if live else _REFERENCE,
        "sources": [
            {
                "citation": (
                    f"Live feed — {meta.get('source')} (${price:.2f}/tCO2e)."
                    if live
                    else f"{CARBON_PRICE_SOURCE}. Reference price "
                    f"${CARBON_PRICE_USD_PER_TCO2:.0f}/tCO2e ({PRICE_YEAR} USD)."
                ),
            }
        ],
        "as_of": str(meta.get("as_of", CARBON_PRICE_AS_OF)),
        "note": (
            "Live carbon-market price."
            if live
            else "Single static reference price; configure CARBON_PRICE_URL / "
            "CARBON_PRICE_USD_PER_TCO2 to go live."
        ),
        "exposed_via": ["GET /api/v1/market", "POST /api/v1/valuation (methodology.carbon_capture)"],
    }


def _fx_domain() -> Dict[str, Any]:
    rates, meta = get_fx_rates()
    live = meta.get("live", False)
    return {
        "id": "fx_rates",
        "label": "Currency exchange rates",
        "category": "finance",
        "status": _AUTHORITATIVE if live else _REFERENCE,
        "sources": [
            {
                "citation": (
                    f"Live feed — {meta.get('source')}: "
                    if live
                    else f"Static snapshot of {FX_SOURCE}: "
                )
                + ", ".join(f"{code} {rates.get(code, c['rate_per_usd'])}/USD" for code, c in CURRENCIES.items()),
                "url": meta.get("url", ""),
            }
        ],
        "as_of": str(meta.get("as_of", FX_AS_OF)),
        "note": (
            "Live FX rates from the European Central Bank."
            if live
            else "Static ECB snapshot; enable ALPHA_LIVE_DATA for live FX."
        ),
        "exposed_via": ["GET /api/v1/market", "GET /api/v1/reference", "POST /api/v1/valuation (fx)"],
    }


def _esv_estimate_counts() -> tuple[int, int]:
    """(flagged estimates, total coefficients) across the biome table."""
    total = len(BIOMES) * (len(ESV_CATEGORIES) + 1)  # four ESV categories + sequestration
    flagged = len(ESV_ESTIMATES) + sum(
        1 for s in SEQUESTRATION.values() if s["basis"] == "estimate"
    )
    return flagged, total


def _esv_note() -> str:
    flagged, total = _esv_estimate_counts()
    return (
        f"Per-biome USD/ha/yr reference yields in {PRICE_YEAR} USD, median basis, each "
        "derived from published ESVD table cells backed by at least 3 value estimates. "
        f"{flagged} of {total} coefficients lack enough published evidence and are "
        "flagged as unverified estimates (see METHODOLOGY.md). Peer-reviewed but static."
    )


def _years(values: Any) -> List[str]:
    """Pull four-digit years out of assorted as-of labels."""
    found = []
    for v in values:
        match = re.search(r"(\d{4})", str(v))
        if match:
            found.append(match.group(1))
    return found


def _anchors_domain() -> Dict[str, Any]:
    """Well-known magnitudes the UI compares headline figures against.

    Reference, not authoritative: published figures that drift year to year and
    are shown behind an "≈". They are a readability aid only — nothing here
    feeds the valuation.
    """
    anchors = anchor_provenance()
    by_source: Dict[str, str] = {}
    for a in anchors:
        by_source.setdefault(a["source"], a["as_of"])
    return {
        "id": "scale_anchors",
        "label": "Human-scale comparison anchors",
        "category": "finance",
        "status": _REFERENCE,
        "sources": [
            {"citation": f"{source} (as of {as_of})"} for source, as_of in sorted(by_source.items())
        ],
        # Anchor as-of values are mixed ("2024", "FY2025", "2025-12"), so take the
        # latest four-digit year rather than a lexical max, which ranks "FY2025"
        # above "2025" and would report a fiscal-year label as the domain's date.
        "as_of": max(_years(a["as_of"] for a in anchors), default="2025"),
        "note": (
            f"{len(anchors)} well-known magnitudes (GDPs, revenues, market caps, national "
            "debts) used to make the headline figures graspable — e.g. \"≈ 2x Apple's market "
            "cap\". Annual flows are only ever compared to flows and present values to "
            "present values. Indicative and rounded; not an input to any valuation."
        ),
        "exposed_via": ["POST /api/v1/valuation (comparisons)"],
    }


def _domains() -> List[Dict[str, Any]]:
    boundaries = boundary_source()
    regions_meta = dataset_provenance()
    return [
        {
            "id": "biome_boundaries",
            "label": "Biome boundaries",
            "category": "geospatial",
            "status": _AUTHORITATIVE,
            "sources": [
                {"citation": boundaries.get("primary", ""), "url": boundaries.get("url", "")},
                {"citation": boundaries.get("seeds", "")},
            ],
            "as_of": boundaries.get("as_of", "2017"),
            "note": boundaries.get("note", "")
            or "Real RESOLVE ecoregion boundaries, generalized for fast classification.",
            "exposed_via": ["POST /api/v1/classify", "POST /api/v1/valuation"],
        },
        {
            "id": "region_catalogue",
            "label": "Region catalogue",
            "category": "geospatial",
            "status": _PLACEHOLDER,
            "sources": [
                {
                    "citation": regions_meta.get("source", {}).get("primary", ""),
                    "url": regions_meta.get("source", {}).get("url", ""),
                }
            ],
            "as_of": regions_meta.get("source", {}).get("as_of", ""),
            "note": f"{regions_meta.get('count', 0)} illustrative named-ecosystem footprints "
            "for map display and Compare.",
            "exposed_via": ["GET /api/v1/regions"],
        },
        {
            "id": "esv_reference",
            "label": "Ecosystem-service reference values",
            "category": "valuation",
            "status": _REFERENCE,
            "sources": [
                {
                    "citation": "Brander, L.M. et al. (2024). Economic values for ecosystem "
                    "services: A global synthesis and way forward. Ecosystem Services 66: 101606 (ESVD).",
                    "url": "https://doi.org/10.1016/j.ecoser.2024.101606",
                },
                {
                    "citation": "de Groot, R. et al. (2012). Global estimates of the value of "
                    "ecosystems and their services in monetary units. Ecosystem Services 1(1): 50-61, "
                    "and Online Supporting Information.",
                    "url": "https://doi.org/10.1016/j.ecoser.2012.07.005",
                },
                {
                    "citation": "de Groot, R., Brander, L., Solomonides, S. (2020). Update of global "
                    "ecosystem service valuation database (ESVD). FSD report 2020-06.",
                },
                {
                    "citation": "Pan, Y. et al. (2024). The enduring world forest carbon sink. "
                    "Nature 631: 563-569.",
                    "url": "https://doi.org/10.1038/s41586-024-07602-x",
                },
                {
                    "citation": "IPCC (2014). 2013 Supplement to the 2006 IPCC Guidelines for "
                    "National Greenhouse Gas Inventories: Wetlands (Ch. 2 & 4).",
                },
                {
                    "citation": "IPCC (2000). Land Use, Land-Use Change and Forestry, Table 1; "
                    "IPCC (2006) Guidelines Vol. 4, Ch. 5.",
                },
            ],
            "as_of": "2024",
            "note": _esv_note(),
            "exposed_via": ["GET /api/v1/reference", "POST /api/v1/valuation"],
        },
        _carbon_domain(),
        _fx_domain(),
        _anchors_domain(),
        {
            "id": "land_cover",
            "label": "Land-cover intactness",
            "category": "geospatial",
            "status": _AUTHORITATIVE,
            "sources": [{"citation": _LC100_CITATION, "url": "https://doi.org/10.5281/zenodo.3939050"}],
            "as_of": "2020",
            "note": "Authoritative CGLS-LC100 legend; the per-class intactness factors and the "
            "per-biome default intactness are heuristic, not literature-derived. Realised value is now "
            "scaled by intactness via per-biome/region defaults; per-polygon raster sampling "
            "(PostGIS) to derive true intactness is still pending.",
            "exposed_via": ["POST /api/v1/valuation (intactness)", "internal (landcover.py)"],
        },
    ]


def _needs() -> List[Dict[str, Any]]:
    """The 'data we still need' roadmap, from the in-repo gap analysis."""
    return [
        {
            "id": "live_fx",
            "label": "Live FX rates",
            "current": "Static ECB reference rates (as of " + FX_AS_OF + ")",
            "planned": "Live FX feed (e.g. central-bank / market API)",
            "why": "Valuations in EUR/BRL drift from reality as rates move.",
            "phase": "Phase 4",
        },
        {
            "id": "live_carbon",
            "label": "Live carbon-market price",
            "current": f"Static ${CARBON_PRICE_USD_PER_TCO2:.0f}/tCO2e reference ({PRICE_YEAR} USD)",
            "planned": "Live voluntary / compliance carbon-market index",
            "why": "Carbon capture is a large share of TEV; its price is the most volatile input.",
            "phase": "Phase 4",
        },
        {
            "id": "raster_land_cover",
            "label": "Satellite land-cover sampling",
            "current": "CGLS-LC100 legend coded; no per-polygon raster lookup",
            "planned": "PostGIS raster sampling of the CGLS-LC100 GeoTIFF per polygon",
            "why": "Lets realised yield reflect intact forest vs. cleared land, not just biome type.",
            "phase": "Phase 4",
        },
        {
            "id": "parcel_boundaries",
            "label": "Parcel-scale boundaries",
            "current": "Real RESOLVE ecoregions (2017), generalized to ~tens of km",
            "planned": "Full-resolution ecoregions + cadastral/parcel overlays for site-level work",
            "why": "Classification now uses real boundaries; parcel precision would let users value an exact lot, not a generalized region.",
            "phase": "Phase 4+",
        },
        {
            "id": "live_esvd",
            "label": "Live ESVD values",
            "current": "Static global ESVD summary values (Brander et al. 2024; de Groot et al. 2012)",
            "planned": "ESVD records / value-transfer functions for region-specific service values",
            "why": "Global summary values are Europe-weighted and thin for tropical, boreal, polar "
            "and desert biomes; region-specific transfer would fill the flagged estimates.",
            "phase": "Phase 4+",
        },
        {
            "id": "report_ingestion",
            "label": "Report / disclosure ingestion",
            "current": "ESV text extraction works on already-extracted text",
            "planned": "PDF→text pipeline (pdfminer/Tika) feeding /api/v1/extract-esv at scale",
            "why": "Bulk-ingest TNFD disclosures and ESVD exports into structured values.",
            "phase": "Phase 4+",
        },
    ]


def data_catalog() -> Dict[str, Any]:
    """Full data catalogue: current sources + the roadmap of what we still need."""
    return {"domains": _domains(), "needs": _needs()}
