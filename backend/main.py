"""alpha backend — ecosystem valuation API.

API-first FastAPI service.

- ``GET /health`` — liveness probe.
- ``POST /api/v1/valuation`` — Phase 2 Total Ecosystem Value (TEV) engine: accepts
  a GeoJSON polygon, computes its geodesic area, and returns a documented,
  citation-backed TEV breakdown in the requested currency (USD / EUR / BRL).
- ``GET /api/v1/reference`` — supported biomes, currencies, and per-sqm reference
  yields, so clients can build biome/currency toggles.

The valuation maths and reference values live in ``valuation.py`` /
``reference_data.py``; the derivations are documented in ``backend/METHODOLOGY.md``.
"""
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from reference_data import (
    BIOMES,
    CURRENCIES,
    DEFAULT_BIOME,
    DEFAULT_CURRENCY,
    YIELD_CATEGORIES,
    biome_per_sqm_usd,
)
from valuation import compute_valuation

app = FastAPI(
    title="alpha API",
    description="Putting nature on the balance sheet — ecosystem valuation API.",
    version="0.2.0",
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


@app.get("/api/v1/reference")
def reference() -> Dict[str, Any]:
    """Supported biomes and currencies plus their per-sqm reference yields.

    Lets the frontend populate biome/currency selectors without hardcoding.
    """
    return {
        "default_biome": DEFAULT_BIOME,
        "default_currency": DEFAULT_CURRENCY,
        "yield_categories": list(YIELD_CATEGORIES),
        "biomes": {
            key: {
                "label": b["label"],
                "yields_per_sqm_usd_year": {
                    c: round(v, 6) for c, v in biome_per_sqm_usd(key).items()
                },
            }
            for key, b in BIOMES.items()
        },
        "currencies": {
            code: {"label": c["label"], "symbol": c["symbol"], "rate_per_usd": c["rate_per_usd"]}
            for code, c in CURRENCIES.items()
        },
    }


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
    """
    geometry = body.to_geometry()
    if not geometry:
        raise HTTPException(
            status_code=422,
            detail="Provide a GeoJSON Polygon/MultiPolygon geometry (type+coordinates or a Feature).",
        )

    chosen_biome = biome or body.biome or DEFAULT_BIOME
    chosen_currency = currency or body.currency or DEFAULT_CURRENCY

    result = compute_valuation(geometry, biome=chosen_biome, currency=chosen_currency)

    if result["area"]["sqm"] <= 0:
        raise HTTPException(
            status_code=422,
            detail="Geometry has zero area — expected a Polygon or MultiPolygon with valid rings.",
        )
    return result
