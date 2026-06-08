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

from typing import Any, Dict, List

from biome_classifier import boundary_source
from reference_data import (
    CARBON_PRICE_USD_PER_TCO2,
    CURRENCIES,
    FX_AS_OF,
)
from regions import dataset_provenance

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


def _domains() -> List[Dict[str, Any]]:
    boundaries = boundary_source()
    regions_meta = dataset_provenance()
    return [
        {
            "id": "biome_boundaries",
            "label": "Biome boundaries",
            "category": "geospatial",
            "status": _PLACEHOLDER,
            "sources": [
                {"citation": boundaries.get("primary", ""), "url": boundaries.get("url", "")},
                {"citation": boundaries.get("mangrove", "")},
                {"citation": boundaries.get("wetland", "")},
            ],
            "as_of": boundaries.get("as_of", ""),
            "note": boundaries.get("note", "")
            or "Coarse, simplified seed footprints — not authoritative boundaries.",
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
                    "citation": "de Groot, R. et al. (2012). Global estimates of the value of "
                    "ecosystems and their services in monetary units. Ecosystem Services 1(1): 50-61 (ESVD).",
                },
                {
                    "citation": "Costanza, R. et al. (2014). Changes in the global value of "
                    "ecosystem services. Global Environmental Change 26: 152-158.",
                },
                {
                    "citation": "Pan, Y. et al. (2011). A Large and Persistent Carbon Sink in the "
                    "World's Forests. Science 333(6045): 988-993.",
                },
            ],
            "as_of": "2012",
            "note": "Per-biome USD/ha/yr reference yields; peer-reviewed but static.",
            "exposed_via": ["GET /api/v1/reference", "POST /api/v1/valuation"],
        },
        {
            "id": "carbon_price",
            "label": "Carbon price",
            "category": "valuation",
            "status": _PLACEHOLDER,
            "sources": [
                {
                    "citation": "IPCC AR6 WGIII (2022), Ch. 7 & Annex III — sub-2 °C mitigation "
                    f"pathways. Reference price ${CARBON_PRICE_USD_PER_TCO2:.0f}/tCO2e.",
                }
            ],
            "as_of": "2022",
            "note": "Single static reference price; not a live market feed.",
            "exposed_via": ["POST /api/v1/valuation (methodology.carbon_capture)"],
        },
        {
            "id": "fx_rates",
            "label": "Currency exchange rates",
            "category": "finance",
            "status": _PLACEHOLDER,
            "sources": [
                {
                    "citation": "Indicative reference rates: "
                    + ", ".join(
                        f"{code} {c['rate_per_usd']}/USD" for code, c in CURRENCIES.items()
                    ),
                }
            ],
            "as_of": FX_AS_OF,
            "note": "Static placeholder rates for the USD/EUR/BRL toggle.",
            "exposed_via": ["GET /api/v1/reference", "POST /api/v1/valuation (fx)"],
        },
        {
            "id": "land_cover",
            "label": "Land-cover intactness",
            "category": "geospatial",
            "status": _AUTHORITATIVE,
            "sources": [{"citation": _LC100_CITATION, "url": "https://doi.org/10.5281/zenodo.3939050"}],
            "as_of": "2020",
            "note": "Authoritative CGLS-LC100 legend + intactness factors are wired; per-polygon "
            "raster sampling is a deployment (PostGIS) concern, not yet applied to live valuations.",
            "exposed_via": ["internal (landcover.py)"],
        },
    ]


def _needs() -> List[Dict[str, Any]]:
    """The 'data we still need' roadmap, from the in-repo gap analysis."""
    return [
        {
            "id": "live_fx",
            "label": "Live FX rates",
            "current": "Static indicative rates (as of " + FX_AS_OF + ")",
            "planned": "Live FX feed (e.g. central-bank / market API)",
            "why": "Valuations in EUR/BRL drift from reality as rates move.",
            "phase": "Phase 4",
        },
        {
            "id": "live_carbon",
            "label": "Live carbon-market price",
            "current": f"Static ${CARBON_PRICE_USD_PER_TCO2:.0f}/tCO2e reference",
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
            "id": "authoritative_boundaries",
            "label": "Authoritative biome boundaries",
            "current": "Coarse simplified seed polygons",
            "planned": "Full WWF Terrestrial Ecoregions (TEOW) + GMW mangroves, dissolved & ingested",
            "why": "Accurate areas and classification depend on real boundaries, not boxes.",
            "phase": "Phase 4",
        },
        {
            "id": "live_esvd",
            "label": "Live ESVD values",
            "current": "Static de Groot et al. 2012 reference yields",
            "planned": "ESVD API for region-specific / updated service values",
            "why": "Reference yields vary by region and have been updated since 2012.",
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
