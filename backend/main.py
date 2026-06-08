"""alpha backend — ecosystem valuation API.

API-first FastAPI service.

- ``GET /health`` — liveness probe.
- ``POST /api/v1/valuation`` — Phase 2 Total Ecosystem Value (TEV) engine: accepts
  a GeoJSON polygon, computes its geodesic area, and returns a documented,
  citation-backed TEV breakdown in the requested currency (USD / EUR / BRL).
- ``GET /api/v1/reference`` — supported biomes, currencies, and per-sqm reference
  yields, so clients can build biome/currency toggles.
- ``GET /api/v1/regions`` — the bundled catalogue of named ecosystems across all
  five biomes, each valued in the requested currency, powering the map overlays
  and the Compare view.
- ``GET /api/v1/datasets`` — the data catalogue: every data domain's source,
  citation, status and "as-of" date, plus the "data we still need" roadmap, for
  the GUI Data Hub.
- ``GET /api/v1/market`` — current carbon price + FX inputs with provenance and
  live/static flags (Phase 4 live market data; see ``live_data.py``).
- ``POST /api/v1/classify`` — Phase 3 data ingestion: classify a GeoJSON polygon
  into a valuation biome using ingested WWF boundary data.
- ``POST /api/v1/extract-esv`` — Phase 3 LLM-assisted extraction of structured ESV
  values from report / TNFD-disclosure text (Ollama-compatible, offline fallback).

The valuation maths and reference values live in ``valuation.py`` /
``reference_data.py``; the derivations are documented in ``backend/METHODOLOGY.md``.
The Phase 3 ingestion layer lives in ``biome_classifier.py``, ``landcover.py`` and
``esv_extraction.py`` and is documented in ``backend/INGESTION.md``.
"""
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from biome_classifier import boundary_source, classify_geometry
from datasets import data_catalog
from esv_extraction import extract_esv_records
from live_data import get_carbon_price, get_fx_rates, market_snapshot
from reference_data import (
    BIOMES,
    CURRENCIES,
    DEFAULT_BIOME,
    DEFAULT_CURRENCY,
    YIELD_CATEGORIES,
    biome_per_sqm_usd,
)
from regions import dataset_provenance, list_regions
from valuation import compute_valuation

app = FastAPI(
    title="alpha API",
    description="Putting nature on the balance sheet — ecosystem valuation API.",
    version="0.3.0",
)

# Allow the Leaflet frontend (served on :3000) to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ValuationRequest(BaseModel):
    """Valuation request body.

    Accepts a bare GeoJSON geometry (``{"type": "Polygon", "coordinates": [...]}``)
    or a wrapped ``Feature``. ``biome`` and ``currency`` are optional and may also
    be supplied as query parameters (the query parameter wins when both are set).
    """

    type: Optional[str] = Field(default=None, examples=["Polygon"])
    coordinates: Optional[List[Any]] = None
    geometry: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    biome: Optional[str] = Field(default=None, examples=["tropical_rainforest"])
    currency: Optional[str] = Field(default=None, examples=["USD"])

    def to_geometry(self) -> Dict[str, Any]:
        """Normalise the body to a single GeoJSON geometry dict."""
        if self.geometry:
            return self.geometry
        if self.type and self.coordinates is not None:
            return {"type": self.type, "coordinates": self.coordinates}
        return {}


@app.get("/health")
def health() -> Dict[str, str]:
    """Liveness probe used by infra and by the frontend on region click."""
    return {"status": "ok", "service": "alpha-backend"}


def _market_for(currency: str) -> Dict[str, Any]:
    """Resolve the carbon price + FX rate for ``currency`` (live or static).

    Returns the numbers to inject into ``compute_valuation`` plus a ``market``
    provenance block (source / as-of / live) to echo back to the client.
    """
    carbon_price, carbon_meta = get_carbon_price()
    rates, fx_meta = get_fx_rates()
    return {
        "carbon_price": carbon_price,
        "fx_rate": rates.get(currency, 1.0),
        "fx_as_of": fx_meta.get("as_of") or None,
        "provenance": {
            "carbon": {"price_usd_per_tco2": round(carbon_price, 4), **carbon_meta},
            "fx": {"base": "USD", "rate_per_usd": round(rates.get(currency, 1.0), 6), **fx_meta},
        },
    }


@app.get("/api/v1/market")
def market() -> Dict[str, Any]:
    """Current market inputs (carbon price + FX) with provenance and live flags.

    Phase 4 live-data surface: lets the Data Hub show whether valuations are
    running on live feeds or the documented static references.
    """
    return market_snapshot()


@app.get("/api/v1/reference")
def reference() -> Dict[str, Any]:
    """Supported biomes and currencies plus their per-sqm reference yields.

    Lets the frontend populate biome/currency selectors without hardcoding.
    Reference yields and FX reflect the live market snapshot when Phase 4 live
    data is enabled, falling back to the documented static references otherwise.
    """
    carbon_price, _ = get_carbon_price()
    rates, _ = get_fx_rates()
    return {
        "default_biome": DEFAULT_BIOME,
        "default_currency": DEFAULT_CURRENCY,
        "yield_categories": list(YIELD_CATEGORIES),
        "biomes": {
            key: {
                "label": b["label"],
                "yields_per_sqm_usd_year": {
                    c: round(v, 6)
                    for c, v in biome_per_sqm_usd(key, carbon_price=carbon_price).items()
                },
            }
            for key, b in BIOMES.items()
        },
        "currencies": {
            code: {
                "label": c["label"],
                "symbol": c["symbol"],
                "rate_per_usd": round(rates.get(code, c["rate_per_usd"]), 6),
            }
            for code, c in CURRENCIES.items()
        },
        "market": market_snapshot(),
    }


@app.get("/api/v1/regions")
def regions(currency: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    """Return the catalogue of named ecosystems, each valued in ``currency``.

    Every region across all five biomes is priced through the same TEV engine as
    ``/api/v1/valuation``, so the frontend can draw the biome map overlays and the
    Compare breakdowns from a single request without re-valuing each polygon.
    """
    chosen_currency = (currency or DEFAULT_CURRENCY).upper()
    if chosen_currency not in CURRENCIES:
        chosen_currency = DEFAULT_CURRENCY
    mkt = _market_for(chosen_currency)
    return {
        "currency": chosen_currency,
        "regions": list_regions(
            chosen_currency,
            carbon_price=mkt["carbon_price"],
            fx_rate=mkt["fx_rate"],
            fx_as_of=mkt["fx_as_of"],
        ),
        "dataset": dataset_provenance(),
        "market": mkt["provenance"],
    }


@app.get("/api/v1/datasets")
def datasets() -> Dict[str, Any]:
    """Data catalogue + roadmap for the GUI Data Hub.

    Returns one entry per data domain (biome boundaries, ESV reference values,
    carbon price, FX, land cover, region catalogue) with its source, citation,
    status and as-of date, plus a ``needs`` roadmap of the data still required.
    Assembled from the same constants the valuation engine uses (see
    ``datasets.py``).
    """
    return data_catalog()


@app.post("/api/v1/valuation")
def valuation(
    body: ValuationRequest,
    biome: Optional[str] = Query(default=None),
    currency: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Compute the Total Ecosystem Value (TEV) breakdown for a GeoJSON polygon.

    The geodesic area of the polygon is computed and used to scale the biome's
    reference yields; results are returned both per sqm/year and as an annual
    total for the whole area, in the requested currency.

    **Phase 3:** when no biome is supplied (query or body), the biome is detected
    from the geometry against ingested WWF boundary data
    (``biome_classifier.classify_geometry``) instead of silently defaulting. The
    detection — including its source and confidence — is returned under
    ``classification``. An explicit biome still wins and is echoed back as an
    ``"explicit"`` classification.
    """
    geometry = body.to_geometry()
    if not geometry:
        raise HTTPException(
            status_code=422,
            detail="Provide a GeoJSON Polygon/MultiPolygon geometry (type+coordinates or a Feature).",
        )

    explicit_biome = biome or body.biome
    chosen_currency = currency or body.currency or DEFAULT_CURRENCY

    if explicit_biome:
        chosen_biome = explicit_biome
        classification = {
            "biome_key": explicit_biome if explicit_biome in BIOMES else DEFAULT_BIOME,
            "biome_label": BIOMES.get(explicit_biome, BIOMES[DEFAULT_BIOME])["label"],
            "confidence": "explicit",
            "source": "biome supplied by caller",
        }
    else:
        classification = classify_geometry(geometry)
        chosen_biome = classification["biome_key"]

    norm_currency = str(chosen_currency or DEFAULT_CURRENCY).upper()
    if norm_currency not in CURRENCIES:
        norm_currency = DEFAULT_CURRENCY
    mkt = _market_for(norm_currency)
    result = compute_valuation(
        geometry,
        biome=chosen_biome,
        currency=chosen_currency,
        carbon_price=mkt["carbon_price"],
        fx_rate=mkt["fx_rate"],
        fx_as_of=mkt["fx_as_of"],
    )

    if result["area"]["sqm"] <= 0:
        raise HTTPException(
            status_code=422,
            detail="Geometry has zero area — expected a Polygon or MultiPolygon with valid rings.",
        )
    result["classification"] = classification
    result["market"] = mkt["provenance"]
    return result


@app.post("/api/v1/classify")
def classify(body: ValuationRequest) -> Dict[str, Any]:
    """Classify a GeoJSON polygon into a valuation biome from ingested boundaries.

    Phase 3 data-ingestion endpoint: locates the geometry's representative point
    inside the bundled WWF-derived biome boundaries and returns the matched biome
    plus provenance. Useful on its own (e.g. to drive map styling) and the same
    logic the valuation endpoint uses for auto-detection.
    """
    geometry = body.to_geometry()
    if not geometry:
        raise HTTPException(
            status_code=422,
            detail="Provide a GeoJSON Polygon/MultiPolygon geometry (type+coordinates or a Feature).",
        )
    return {
        "classification": classify_geometry(geometry),
        "boundary_dataset": boundary_source(),
    }


class ExtractESVRequest(BaseModel):
    """Report / disclosure text to mine for structured ESV values."""

    text: str = Field(..., examples=["Carbon sequestration was valued at $120 per ha per year."])
    backend: Optional[str] = Field(
        default="auto",
        description="'auto' (LLM if OLLAMA_HOST set, else regex), 'deterministic', or 'llm'.",
        examples=["auto"],
    )
    model: Optional[str] = None


@app.post("/api/v1/extract-esv")
def extract_esv(body: ExtractESVRequest) -> Dict[str, Any]:
    """Extract structured ESV values from report / TNFD-disclosure text.

    Phase 3 LLM-assisted ingestion: pulls ``{service, value, currency, unit,
    context}`` records out of prose. Uses an Ollama/llama.cpp-compatible model when
    one is configured (``OLLAMA_HOST``), and transparently falls back to a
    deterministic regex extractor otherwise — so it always returns a result.
    """
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=422, detail="Provide non-empty 'text' to extract from.")
    return extract_esv_records(body.text, backend=body.backend or "auto", model=body.model)
