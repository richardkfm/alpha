# alpha — Architecture

> **alpha** — _"Putting nature on the balance sheet."_

`alpha` is a full-stack geospatial web platform and API that calculates and
visualizes the true financial value of natural ecosystems. Our core thesis: a
standing rainforest is one of the most valuable financial assets on earth, but it
is systematically underpriced because its ecosystem services (carbon capture,
global cooling, water filtration, biodiversity) are invisible on any balance
sheet. `alpha` makes them visible and quantifiable.

- **Repo:** github.com/richkfm/alpha
- **License:** AGPL-3.0

---

## Target Audience & User Goals

1. **Policymakers** — Need a clear, defensible map showing what is at stake
   economically when a protected area is rezoned. _"How much value does 1 sqm of
   this Amazon rainforest generate per year?"_
2. **Investors & ESG Funds** — Need a financial API that returns structured
   ecosystem service valuations for a geographic polygon so they can price natural
   capital into portfolios, bonds, and risk assessments.
3. **Journalists** — Need an intuitive, beautiful map-based interface to explore
   and communicate why preserving the Congo Basin is worth more than clearing it
   for farmland.

---

## Architecture Overview

**Monorepo structure:**

- `/backend` — Python (FastAPI), PostgreSQL + PostGIS, SQLAlchemy + GeoAlchemy2
- `/frontend` — Vue.js (Vite-based Vue 3 SPA), Leaflet.js for the world map,
  AGPL-3.0 compliant
- `docker-compose.yml` — Root-level orchestration for all services (self-hosted,
  Proxmox-ready)

**Key design principle:** The backend is an API-first service. The frontend is
the first consumer of that API. External trading platforms and policy dashboards
can consume the same API directly.

```
┌──────────────┐      HTTP/JSON      ┌──────────────┐      SQL       ┌──────────────┐
│   frontend   │ ──────────────────> │   backend    │ ─────────────> │  db (PostGIS)│
│ Vue 3 + Vite │   /api/v1/valuation │   FastAPI    │   GeoAlchemy2  │  PostgreSQL  │
│  Leaflet.js  │ <────────────────── │              │ <───────────── │      15      │
└──────────────┘                     └──────────────┘                └──────────────┘
   port 3000                            port 8000                        port 5432
```

---

## Core Valuation Methodology

Ecosystem services are grouped into these financial yield categories, expressed
**per sqm per year**:

| Category | Definition |
| --- | --- |
| **Carbon Capture Yield (USD)** | Tonnes of CO₂ absorbed × current carbon credit price |
| **Climate Regulation Yield (USD)** | Evapotranspiration-based cooling effect translated into avoided HVAC/energy costs |
| **Water Filtration Yield (USD)** | Volume of clean water cycled × cost of equivalent industrial water treatment |
| **Biodiversity Premium (USD)** | Based on ESVD database values for biome type |
| **Soil Nutrient Value (USD)** | Replacement cost of nutrients held in the ecosystem, representing the true cost of converting land to agriculture or construction |

> **Total Ecosystem Value (TEV) = Sum of all yield categories per sqm per year**

Initially these are well-documented **mock calculations** using scientifically
defensible reference values. In later phases they connect to real-time data
sources (Copernicus satellite data, ESVD API, carbon market prices).

---

## Development Phases

### Phase 1 — Foundation (current sprint)

- Monorepo scaffolding with `/backend` and `/frontend`
- Docker Compose environment (PostGIS, FastAPI, Node frontend)
- Full-screen world map with hardcoded GeoJSON overlays for the 4 major rainforest
  regions
- Clicking a region shows a panel with mock TEV data from the backend API

### Phase 2 — Valuation Engine

- Build the real TEV calculation module in FastAPI using documented reference
  values from ESVD and IPCC carbon pricing
- `POST /api/v1/valuation` endpoint accepts a GeoJSON polygon and returns a full
  structured TEV breakdown
- Document every calculation formula with scientific citations in the codebase
- Add a currency toggle (USD / EUR / BRL)

### Phase 3 — Data Ingestion

- Ingest real biome boundary data (e.g., WWF Terrestrial Ecoregions, Global Forest
  Watch)
- Integrate Copernicus land cover data for dynamic land-use overlays
- Build an LLM-assisted parsing module (Ollama/llama.cpp-compatible) to extract ESV
  values from PDF scientific reports and TNFD disclosures

### Phase 4 — API & Export Layer

- Harden the API with versioning, rate limiting, and API key authentication (for
  commercial users under AGPL dual-licensing)
- Add PDF/CSV export for investor reports
- Add embeddable widget (iframe snippet) for third-party policy dashboards

---

## The Web App (UX)

The visual centrepiece is a **full-screen world map** (Leaflet.js):

- Highlighted overlay polygons for the world's major rainforest biomes:
  - **Amazon Basin** (Brazil, Peru, Colombia, Bolivia, Ecuador, Venezuela)
  - **Congo Basin** (DRC, Republic of Congo, Cameroon, Gabon)
  - **Southeast Asian Rainforests** (Indonesia, Malaysia, Papua New Guinea, Borneo)
  - **Central American Rainforests** (Costa Rica, Panama)
- Clicking a polygon opens a **side panel** that shows:
  - Ecosystem name, country/region
  - Total area (sqm and hectares)
  - Breakdown of all ecosystem service values (carbon, water, climate,
    biodiversity, soil)
  - **Total Ecosystem Value (TEV) in USD per sqm per year**
  - A comparison callout: _"This region generates more annual economic value
    standing than the GDP contribution of [industry X] in this country"_
- A global search/query bar so users can enter custom coordinates or paste a
  GeoJSON polygon to get a valuation on demand
- Clean, dark-themed UI with teal/green accents to convey the
  environmental-financial theme. Light/dark mode toggle included (dark is default).

---

## Naming Convention

The project name **`alpha` is strictly lowercase** everywhere — in files, code,
identifiers, and documentation.
