# alpha — backend

API-first FastAPI service that computes the **Total Ecosystem Value (TEV)** of a
geographic area. Part of the [`alpha`](../README.md) monorepo.

## Stack

- **FastAPI** + **uvicorn**
- **SQLAlchemy** + **GeoAlchemy2** (PostGIS access — wired in Phase 2)
- **PostgreSQL 15 + PostGIS** (via the root `docker-compose.yml`)

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe → `{"status": "ok", "service": "alpha-backend"}` |
| `POST` | `/api/v1/valuation` | GeoJSON polygon → full TEV breakdown (geodesic area, per-sqm + area totals, currency). **Phase 3:** auto-detects the biome when none is supplied (`classification` in the response) |
| `GET` | `/api/v1/reference` | Supported biomes & currencies + their per-sqm reference yields |
| `POST` | `/api/v1/classify` | _(Phase 3)_ GeoJSON polygon → detected biome from ingested WWF boundaries + dataset provenance |
| `POST` | `/api/v1/extract-esv` | _(Phase 3)_ report / TNFD text → structured ESV records (Ollama-compatible, offline regex fallback) |
| `GET` | `/docs` | Auto-generated Swagger UI |

### `POST /api/v1/valuation` (Phase 2 engine)

Request body — a GeoJSON polygon/multipolygon (bare geometry or wrapped `Feature`).
Optional `biome` and `currency` may be set in the body or as query params
(`?biome=mangrove&currency=EUR`); the query param wins.

```json
{ "type": "Polygon", "coordinates": [[[-60,-3],[-60,-2],[-59,-2],[-59,-3],[-60,-3]]] }
```

Response:

```json
{
  "biome": "Tropical Rainforest",
  "biome_key": "tropical_rainforest",
  "currency": "USD",
  "currency_symbol": "$",
  "area": { "sqm": 12290000000.0, "hectares": 1229000.0 },
  "yields_per_sqm_year": {
    "carbon_capture": 0.0069,
    "climate_regulation": 0.036,
    "water_filtration": 0.02,
    "biodiversity_premium": 0.05,
    "soil_nutrient_value": 0.012
  },
  "yields_total_year": { "carbon_capture": 84801000.0, "...": "..." },
  "total_ecosystem_value_per_sqm_year": 0.1249,
  "total_ecosystem_value_per_year": 1535021000.0,
  "fx": { "base": "USD", "rate_per_usd": 1.0, "as_of": "2025-12" },
  "methodology": { "carbon_capture": { "formula": "...", "citation": "..." } },
  "methodology_note": "Phase 2 valuation engine. ... See backend/METHODOLOGY.md."
}
```

The geodesic area is computed from the polygon (spherical-excess formula), the
biome's reference yields are scaled by area, and everything is converted to the
requested currency. **Formulas, reference values, and citations are documented in
[`METHODOLOGY.md`](./METHODOLOGY.md)** (sources: de Groot et al. 2012 / ESVD,
Costanza et al. 2014, Pan et al. 2011, IPCC AR6 WGIII).

Code layout:

- `valuation.py` — geodesic area + TEV computation
- `reference_data.py` — biome reference table, carbon price, FX rates (with citations)
- `biome_classifier.py` — _(Phase 3)_ classify a polygon into a biome from ingested
  WWF boundaries (`data/wwf_biomes.geojson`)
- `landcover.py` — _(Phase 3)_ Copernicus CGLS-LC100 legend → biome hint + intactness
- `esv_extraction.py` — _(Phase 3)_ LLM-assisted (Ollama-compatible) + regex ESV parser
- `ingest.py` — _(Phase 3)_ ingestion CLI (`validate` / `classify` / `refresh`)
- `tests/` — unit tests for the engine and the Phase 3 ingestion layer (`python -m pytest`)

The Phase 3 ingestion layer is documented in [`INGESTION.md`](./INGESTION.md).

## Run with Docker (recommended)

From the repo root:

```bash
docker compose up --build backend db
```

## Run standalone (local dev)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adjust DATABASE_URL if needed
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Roadmap

**Phase 3 ✅** ingests real biome boundaries (WWF ecoregions) to auto-detect the
biome, adds the Copernicus land-cover intactness layer, and an LLM-assisted ESV
extractor — see [`INGESTION.md`](./INGESTION.md). **Phase 4** connects carbon prices
and FX rates to live feeds and hardens the API (versioning, auth, rate limiting,
export).
