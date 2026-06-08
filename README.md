<img width="2316" height="746" alt="alpha" src="https://github.com/user-attachments/assets/e4a98274-dd61-436b-b9b9-e28751f4aafe" />

# alpha

> _Putting nature on the balance sheet._

`alpha` is a full-stack geospatial web platform and API that calculates and
visualizes the true financial value of natural ecosystems. A standing rainforest
is one of the most valuable financial assets on earth — `alpha` makes its
ecosystem services (carbon capture, cooling, water filtration, biodiversity, soil
nutrients) visible and quantifiable as a **Total Ecosystem Value (TEV)** per sqm
per year.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full methodology and phased
roadmap.

## Preview

Clicking a rainforest region confirms backend connectivity and opens a side panel
with its full Total Ecosystem Value breakdown:

![alpha — clicking the Amazon Basin shows the ecosystem value side panel](./docs/screenshot.png)

---

## What it does

- **Total Ecosystem Value (TEV) engine** — geodesic-area valuation of any GeoJSON
  polygon across **eleven biomes**, broken into five ecosystem-service yields
  (carbon capture, climate regulation, water filtration, biodiversity, soil
  nutrients), reported per sqm/year and area-scaled, in USD / EUR / BRL.
- **Automatic biome detection** — classifies a polygon against real **RESOLVE
  Ecoregions 2017** boundaries, layered with curated seeds for the land-use and
  freshwater types RESOLVE omits (cropland, peri-urban, lakes & rivers).
- **Land-cover intactness** — realised yield is scaled by how intact the ground
  cover is (Copernicus CGLS-LC100 legend), with the intact *potential* shown
  alongside.
- **Balance-sheet framing** — capitalises the perpetual annual flow into a
  standing **natural-asset value**, and reframes conversion as a permanent,
  externalised **liability** with a one-time carbon debt and irreversible
  "red line" flags, rather than a price a developer can outbid.
- **Live market data** — carbon price + FX (ECB via Frankfurter) with a
  transparent fallback to documented static references when a feed is unreachable.
- **ESV text extraction** — pulls structured ecosystem-service values out of
  report / TNFD-disclosure prose (Ollama-compatible, with an offline regex
  fallback).
- **Web app** — 3D MapLibre globe + 2D Leaflet map; polygon / value-bubble / heat
  display styles; a side-by-side **Compare** dashboard; a **Data Hub** with live
  tools and full provenance; custom-area search; and a dark/light theme.

## Conversion is a liability, not a price

A head-to-head _"value standing vs. value built"_ turns nature into a line item a
developer can simply outbid — conceding that ecosystems are substitutable and
that destroying a parcel costs no more than that parcel's isolated value. `alpha`
rejects both. Alongside the scientific TEV (which it leaves unchanged), it carries
a deliberately value-laden **systemic / irreversibility layer** built on three
principles:

- **A liability, not a price.** Conversion is reported as the present value of the
  services lost _forever_ — a permanent, externalised debt borne by the public,
  downstream communities, and future generations, not by whoever clears the land.
  It is **never netted against development revenue**: a debt owed to others in
  perpetuity, not a price the project can buy out.
- **Systemic weight.** Rare, intact, load-bearing land is worth _more_ than the
  isolated parcel, because fragmenting it degrades the wider network. A systemic
  premium of `1 + scarcity × intactness` captures this, plus a one-time, largely
  irreversible **carbon-stock debt** released when standing vegetation and soil
  are cleared (distinct from the annual sequestration flow).
- **Red lines, not line items.** Non-substitutable, irreversible losses —
  extinctions, ancient soil & peat, permafrost, aquifers — are **flagged, not
  monetised**. They sit outside the money figures on purpose: they cannot be
  recreated at any price, so they must never be traded against revenue.

This makes the full, distributed, permanent cost of conversion legible while
refusing the premise that nature is for sale. The valuation surfaces it under
`systemic`, `conversion_liability`, and `red_lines`, and the web app renders it in
the side panel's _"If this land were converted"_ section. Full derivation:
[`backend/METHODOLOGY.md`](./backend/METHODOLOGY.md) §6.

## Stack

| Service | Tech | Port |
| --- | --- | --- |
| `frontend` | Vue 3 + Vite, MapLibre GL + Leaflet.js | 3000 |
| `backend` | FastAPI, SQLAlchemy + GeoAlchemy2 | 8000 |
| `db` | PostgreSQL 15 + PostGIS | 5432 |

## Quickstart

```bash
docker compose up --build
```

Then open:

- **Web app:** http://localhost:3000 — full-screen 3D globe (with a 2D flat map)
  showing named ecosystems across all valuation biomes. Click any region for its
  TEV breakdown; switch Map / Compare / Data modes; toggle USD / EUR / BRL.
- **API health:** http://localhost:8000/health
- **API docs (Swagger):** http://localhost:8000/docs

### Try the valuation endpoint

The Phase 2 engine computes the polygon's geodesic area and returns a documented,
citation-backed TEV breakdown (per sqm/year and an area-scaled annual total) in
the requested currency. Methodology: [`backend/METHODOLOGY.md`](./backend/METHODOLOGY.md).

```bash
curl -X POST "http://localhost:8000/api/v1/valuation?currency=EUR" \
  -H 'Content-Type: application/json' \
  -d '{"type":"Polygon","coordinates":[[[-60,-3],[-60,-2],[-59,-2],[-59,-3],[-60,-3]]]}'
```

### Phase 3 — data ingestion

The biome is now **detected from the polygon** against ingested RESOLVE ecoregion
boundaries (no need to pass `biome`); the detection is returned under
`classification`. A dedicated `POST /api/v1/classify` returns just the biome, and
`POST /api/v1/extract-esv` mines structured ecosystem-service values out of report /
TNFD text (Ollama-compatible, with an offline fallback). See
[`backend/INGESTION.md`](./backend/INGESTION.md).

```bash
# Detect the biome for a polygon
curl -X POST http://localhost:8000/api/v1/classify \
  -H 'Content-Type: application/json' \
  -d '{"type":"Polygon","coordinates":[[[-65,-5],[-60,-5],[-60,-2],[-65,-2],[-65,-5]]]}'
```

## Repository layout

```
alpha/
├── ARCHITECTURE.md        # methodology + phased roadmap
├── docker-compose.yml     # db + backend + frontend
├── backend/               # FastAPI valuation API
└── frontend/              # Vue 3 + Vite — MapLibre globe + Leaflet flat map
```

## License

[AGPL-3.0](./LICENSE).
