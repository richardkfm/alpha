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
| `POST` | `/api/v1/valuation` | Accepts a GeoJSON polygon, returns a mock TEV breakdown |
| `GET` | `/docs` | Auto-generated Swagger UI |

### `POST /api/v1/valuation`

Request body — a GeoJSON polygon (bare geometry or wrapped `Feature`):

```json
{ "type": "Polygon", "coordinates": [[[-60,-3],[-60,-2],[-59,-2],[-59,-3],[-60,-3]]] }
```

Response (Phase 1 mock):

```json
{
  "biome": "Tropical Rainforest",
  "area_sqm": 1,
  "currency": "USD",
  "yields": {
    "carbon_capture_usd": 2.40,
    "climate_regulation_usd": 1.80,
    "water_filtration_usd": 0.95,
    "biodiversity_premium_usd": 1.20,
    "soil_nutrient_value_usd": 0.65
  },
  "total_ecosystem_value_usd": 7.00,
  "methodology_note": "Mock values based on ESVD 2020 median tropical forest valuations. Phase 2 will connect to live data sources."
}
```

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

## Roadmap

The per-sqm reference constants in `main.py` are Phase 1 placeholders. **Phase 2**
replaces them with a documented, citation-backed valuation engine (ESVD + IPCC
carbon pricing) and adds a currency toggle (USD / EUR / BRL).
