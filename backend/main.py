"""alpha backend — ecosystem valuation API.

API-first FastAPI service. Phase 1 exposes a health check and a mock Total
Ecosystem Value (TEV) endpoint. Phase 2 replaces the mock constants below with
the real valuation engine (ESVD + IPCC carbon pricing, with citations).
"""
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="alpha API",
    description="Putting nature on the balance sheet — ecosystem valuation API.",
    version="0.1.0",
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

# ---------------------------------------------------------------------------
# Mock valuation reference values (USD per sqm per year).
#
# Phase 1 placeholders. Figures are illustrative and derived from the order of
# magnitude of ESVD 2020 median tropical-forest valuations. Phase 2 will replace
# these with a documented, citation-backed calculation engine.
# ---------------------------------------------------------------------------
CARBON_CAPTURE_USD = 2.40
CLIMATE_REGULATION_USD = 1.80
WATER_FILTRATION_USD = 0.95
BIODIVERSITY_PREMIUM_USD = 1.20
SOIL_NUTRIENT_VALUE_USD = 0.65

METHODOLOGY_NOTE = (
    "Mock values based on ESVD 2020 median tropical forest valuations. "
    "Phase 2 will connect to live data sources."
)


class GeoJSONPolygon(BaseModel):
    """Permissive GeoJSON polygon body.

    Accepts either a bare geometry (``{"type": "Polygon", "coordinates": [...]}``)
    or a wrapped ``Feature``. Phase 2 will validate geometry and compute true area.
    """

    type: Optional[str] = Field(default=None, examples=["Polygon"])
    coordinates: Optional[List[Any]] = None
    geometry: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None


@app.get("/health")
def health() -> Dict[str, str]:
    """Liveness probe used by infra and by the frontend on region click."""
    return {"status": "ok", "service": "alpha-backend"}


@app.post("/api/v1/valuation")
def valuation(polygon: GeoJSONPolygon) -> Dict[str, Any]:
    """Return a mock Total Ecosystem Value (TEV) breakdown for a GeoJSON polygon.

    Phase 1: returns fixed per-sqm reference values regardless of the input
    geometry. The polygon is accepted and echoed in spirit so clients can wire up
    the real request shape now.
    """
    yields = {
        "carbon_capture_usd": CARBON_CAPTURE_USD,
        "climate_regulation_usd": CLIMATE_REGULATION_USD,
        "water_filtration_usd": WATER_FILTRATION_USD,
        "biodiversity_premium_usd": BIODIVERSITY_PREMIUM_USD,
        "soil_nutrient_value_usd": SOIL_NUTRIENT_VALUE_USD,
    }
    total = round(sum(yields.values()), 2)

    return {
        "biome": "Tropical Rainforest",
        "area_sqm": 1,
        "currency": "USD",
        "yields": yields,
        "total_ecosystem_value_usd": total,
        "methodology_note": METHODOLOGY_NOTE,
    }
