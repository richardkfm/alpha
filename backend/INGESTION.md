# alpha — Data Ingestion (Phase 3)

Phase 2 valued a polygon against a biome the caller chose (or the default). Phase 3
adds the **ingestion layer** that grounds a valuation in real-world data:

1. **Biome boundaries** — classify a polygon into a valuation biome from ingested
   WWF ecoregion boundaries instead of defaulting/accepting it as input.
2. **Copernicus land cover** — translate on-the-ground land-cover into an
   *intactness factor* (intact forest vs. cleared cropland) that scales realised
   yield.
3. **LLM-assisted ESV extraction** — pull structured ecosystem-service values out
   of scientific reports and TNFD disclosures, Ollama/llama.cpp-compatible, with an
   offline regex fallback.

Everything here is pure-Python and dependency-free (standard library only),
matching the valuation engine. Large raster/vector datasets are **not** vendored;
the modules are the deterministic, unit-tested logic that real ingestion feeds.

---

## 1. Biome boundaries — `biome_classifier.py`

- **Data:** `data/wwf_biomes.geojson` — a coarse, simplified seed `FeatureCollection`.
  Each feature carries a `biome_key` (one of `reference_data.BIOMES`) and is derived
  from the WWF **Terrestrial Ecoregions of the World** (Olson et al. 2001) biome
  classes, plus mangrove and inland-wetland references. **Not authoritative** —
  illustrative footprints for in-repo classification.
- **Logic:** `classify_geometry(geometry)` computes a representative interior point
  and runs a ray-casting point-in-polygon test against the boundaries. When a point
  falls inside several boundaries the most *specific* (smallest) wins (e.g. a
  mangrove patch inside a wider tropical region). No match → the default biome with
  `confidence: "default"`.
- **Output:** `{biome_key, biome_label, matched_region, wwf_biome, point,
  confidence, source}`.

```bash
python ingest.py classify -62 -4      # -> Amazon Basin, tropical_rainforest
python ingest.py validate             # check the bundled dataset is well-formed
```

### Refreshing from the authoritative source

The full TEOW / Copernicus layers need network access and GIS tooling, so they are
not downloaded automatically. `python ingest.py refresh` prints the procedure and
source URLs. In short: download TEOW → dissolve ecoregions to the WWF biome class →
map each class to one of alpha's five valuation biomes → simplify → export GeoJSON
with a `biome_key` per feature → `python ingest.py validate`.

| WWF biome class | alpha `biome_key` |
| --- | --- |
| Tropical & Subtropical Moist Broadleaf Forests | `tropical_rainforest` |
| Temperate Broadleaf / Conifer Forests | `temperate_forest` |
| Mangroves (GMW overlay) | `mangrove` |
| Flooded Grasslands & Savannas / Ramsar wetlands | `wetland` |
| Temperate Grasslands, Savannas & Shrublands | `temperate_grassland` |

---

## 2. Copernicus land cover — `landcover.py`

Ships the **CGLS-LC100** (Copernicus Global Land Service, Dynamic Land Cover, 100 m,
collection 3) discrete-classification legend and maps each class code to:

- a **biome hint** (cross-checks the coarse boundary classifier), and
- an **intactness factor** in `[0, 1]` — the share of the intact-biome reference
  yield a parcel in that land-cover class is assumed to still deliver (closed
  broadleaf forest ≈ 1.0, cropland ≈ 0.1, urban = 0.0).

`aggregate_intactness({class_code: area_fraction})` returns the area-weighted
intactness for a polygon's land-cover mix — the value a deployment multiplies
against the reference yield once it samples the CGLS-LC100 raster (via PostGIS /
the ingestion pipeline). The legend mapping is unit-tested offline.

> Source: Buchhorn, M. et al. (2020). *Copernicus Global Land Service: Land Cover
> 100m: collection 3.* Zenodo. https://doi.org/10.5281/zenodo.3939050

---

## 3. LLM-assisted ESV extraction — `esv_extraction.py`

Extracts `{service, value, currency, unit, context}` records from report text into
alpha's canonical `YIELD_CATEGORIES`.

- **`deterministic`** (default, offline): a transparent regex pass — pairs a service
  keyword with a monetary figure that has a currency marker or per-area/per-year
  unit. Reproducible; the CI baseline.
- **`llm`**: an **Ollama / llama.cpp-compatible** HTTP backend (the project's
  self-hosted, AGPL-friendly inference target). Standard-library `urllib` only — no
  new dependency. Configured via:
  - `OLLAMA_HOST` (default `http://localhost:11434`)
  - `OLLAMA_MODEL` (default `llama3.1`)
  On any error (model down, unparseable output) it **falls back to deterministic**
  so the call never hard-fails.
- **`auto`** (default): LLM when `OLLAMA_HOST` is set, else deterministic.

PDF → text extraction is out of scope here — feed already-extracted text
(pdfminer/Tika in the ingestion pipeline) into `extract_esv_records(text)`.

```bash
curl -X POST http://localhost:8000/api/v1/extract-esv \
  -H 'Content-Type: application/json' \
  -d '{"text":"Water purification was valued at US$3,000 per ha per year."}'
```

---

## API surface (Phase 3 additions)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/classify` | GeoJSON → detected biome + boundary-dataset provenance |
| `POST` | `/api/v1/extract-esv` | report text → structured ESV records |
| `POST` | `/api/v1/valuation` | now **auto-detects** the biome when none is supplied; the detection is returned under `classification` |

## Tests

```bash
python -m pytest
```

Covers the classifier (`test_biome_classifier.py`), land-cover legend
(`test_landcover.py`), ESV extractor incl. LLM fallback (`test_esv_extraction.py`),
and the Phase 3 endpoints (`test_api.py`).
