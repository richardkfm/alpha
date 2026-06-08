# alpha — Valuation Methodology (Phase 2)

This document explains how the `POST /api/v1/valuation` endpoint turns a GeoJSON
polygon into a **Total Ecosystem Value (TEV)**. Every formula and reference value
is documented here and in the code (`backend/valuation.py`,
`backend/reference_data.py`).

> **Status:** the engine uses documented, peer-reviewed *reference values* per
> biome. They are scientifically defensible estimates, **not** live measurements.
> **Phase 3 (done)** ingests real WWF ecoregion boundaries so the biome is detected
> from the polygon rather than defaulted/accepted as input, and adds a Copernicus
> land-cover intactness layer and an LLM-assisted ESV extractor — see
> [`INGESTION.md`](./INGESTION.md). Phase 4 wires carbon prices and FX rates to live
> feeds.

---

## 1. Area

The polygon area is computed geodesically (not in planar degrees) using the
spherical-excess formula (Chamberlain & Duquette, JPL — the same algorithm used
by OpenLayers and Google Maps geometry), on a sphere of mean Earth radius
`R = 6,371,008.8 m` (IUGG).

For a `Polygon`, the area is the exterior ring minus any holes; for a
`MultiPolygon`, it is the sum over member polygons. Result in **m²**, with
hectares = m² ÷ 10,000.

See `geodesic_area_sqm()` in `valuation.py`.

---

## 2. Yield categories

All reference values are stored as **USD per hectare per year** and converted to
**USD per m² per year** by dividing by 10,000.

| Category | Formula | Source |
| --- | --- | --- |
| **Carbon Capture** | `sequestration (tCO₂/ha/yr) × carbon price (USD/tCO₂) ÷ 10,000` | Pan et al. 2011 (net forest sink); IPCC AR6 WGIII 2022 (carbon price) |
| **Climate Regulation** | ESVD climate-regulation reference (USD/ha/yr) ÷ 10,000, excluding the carbon already counted | de Groot et al. 2012; Costanza et al. 2014 |
| **Water Filtration** | ESVD water purification + flow regulation (USD/ha/yr) ÷ 10,000 | de Groot et al. 2012 (ESVD) |
| **Biodiversity Premium** | ESVD genetic resources + habitat/refugia (USD/ha/yr) ÷ 10,000 | de Groot et al. 2012 (ESVD) |
| **Soil Nutrient Value** | ESVD erosion prevention + soil-fertility maintenance (USD/ha/yr) ÷ 10,000 | de Groot et al. 2012 (ESVD) |

**Carbon price:** a single transparent reference of **$30/tCO₂** is applied to
every biome's sequestration rate. It sits between voluntary nature-based credit
prices (~$10–15) and central social-cost-of-carbon / compliance estimates ($50+),
within the IPCC AR6 WGIII range for sub-2 °C pathways.

### Total

```
TEV_per_sqm_year = Σ (five category yields, per m²/yr)
TEV_per_year     = TEV_per_sqm_year × area_sqm
```

Both the per-m² and area-scaled totals are returned, per category and in total.

---

## 3. Biome reference table

Reference values (USD/ha/yr unless noted) live in `reference_data.py::BIOMES`.
Values are deliberately conservative (lower-to-mid of published ranges).

| Biome | Sequestration (tCO₂/ha/yr) | Climate | Water | Biodiversity | Soil |
| --- | --- | --- | --- | --- | --- |
| Tropical Rainforest | 2.3 | 360 | 200 | 500 | 120 |
| Temperate Forest | 1.5 | 250 | 150 | 250 | 100 |
| Boreal Forest (Taiga) | 1.2 | 180 | 120 | 150 | 150 |
| Mangrove | 6.0 | 500 | 900 | 800 | 300 |
| Inland Wetland | 1.0 | 400 | 3,000 | 1,200 | 250 |
| Freshwater (Lakes & Rivers) | 0.0 | 300 | 3,500 | 600 | 0 |
| Temperate Grassland | 0.5 | 80 | 60 | 120 | 200 |
| Cropland & Agriculture | 0.3 | 60 | 40 | 50 | 180 |
| Peri-urban / Managed Open Land | 0.6 | 150 | 120 | 90 | 120 |
| Tundra | 0.3 | 40 | 30 | 60 | 80 |
| Desert & Xeric Shrubland | 0.1 | 20 | 10 | 40 | 20 |

The "ordinary land" biomes (boreal forest, freshwater, cropland, peri-urban) plus
tundra and desert draw on the same ESVD biome groups (de Groot et al. 2012). They
count **regulating and supporting services only** — provisioning revenue such as
crop yield or drinking-water supply is excluded — so the figure represents the
ecosystem value *lost when the land is sealed or converted*, the quantity that is
normally invisible in a rezoning decision. The default biome is
`tropical_rainforest`.

As of **Phase 4**, the biome is detected from the polygon against **real RESOLVE
Ecoregions 2017** boundaries (Dinerstein et al.; `data/ecoregions.geojson`),
generalized for fast offline point-in-polygon classification and mapped from the
14 RESOLVE biomes to alpha's valuation biomes. Curated seeds
(`data/wwf_biomes.geojson`) layer on top for the land-use/freshwater types RESOLVE
omits (cropland, peri-urban, lakes). Realised value is then scaled by land-cover
**intactness** (`landcover.py`), and the annual flow is **capitalised** into a
present-value standing asset at a 3% reference discount rate. As of **Phase 3**, the biome is
detected from the polygon against ingested WWF ecoregion boundaries
(`biome_classifier.py`, `data/wwf_biomes.geojson`) when the caller does not supply
one; the detection and its provenance are returned under `classification`. See
[`INGESTION.md`](./INGESTION.md).

---

## 4. Currency

The engine returns values in **USD** (default), **EUR**, or **BRL**. Conversion
uses indicative static rates relative to USD (`reference_data.py::CURRENCIES`,
`as_of` 2025-12). Select via the `currency` query parameter or request-body
field. Phase 4 connects to a live FX source.

---

## 5. Worked example

A 1 ha (10,000 m²) tropical-rainforest polygon, in USD:

```
carbon_capture      = 2.3 × 30 / 10,000   = 0.0069  USD/m²/yr  →  69    USD/yr
climate_regulation  = 360 / 10,000        = 0.0360  USD/m²/yr  →  360   USD/yr
water_filtration    = 200 / 10,000        = 0.0200  USD/m²/yr  →  200   USD/yr
biodiversity_premium= 500 / 10,000        = 0.0500  USD/m²/yr  →  500   USD/yr
soil_nutrient_value = 120 / 10,000        = 0.0120  USD/m²/yr  →  120   USD/yr
------------------------------------------------------------------------------
TEV                 = 0.1249 USD/m²/yr    →  1,249 USD/yr for the hectare
```

---

## 6. Standing-asset value & the cost of conversion

Two layers sit on top of the annual TEV. Both are reported separately so the
scientific per-m²/yr figure stays untouched.

**Capitalisation.** The annual flow is a perpetuity; its present value is
`asset = annual ÷ discount_rate` (3% reference, between Stern ~1.4% and Nordhaus
~4–5%). This is the land's value *as a standing natural asset* — a balance-sheet
number, not an annual one.

**Cost of conversion — deliberately *not* a price to outbid.** Converting land is
framed as a permanent, externalised **liability**, never netted against
development revenue, because a parcel's loss is more than its isolated value:

- **Systemic premium** — `multiplier = 1 + scarcity × intactness`. Rare, intact
  systems are load-bearing; fragmenting one degrades the wider network beyond the
  parcel. The liability uses the systemic-weighted asset value.
- **Irreversible carbon debt** — clearing releases the standing carbon *stock*
  (vegetation + soil, `BIOME_CARBON_STOCK_TCO2_HA`) once, priced at the carbon
  price. Distinct from the annual sequestration flow.
- **Red lines** — non-substitutable / irreversible losses (extinction, ancient
  soil & peat, permafrost, aquifers) are **flagged, not monetised**. They cannot
  be netted against revenue at any price and are listed outside the figures.

These weights are value-laden by design and kept separate from the ESV in
`reference_data.py` (`BIOME_SCARCITY_WEIGHT`, `BIOME_CARBON_STOCK_TCO2_HA`,
`BIOME_RED_LINES`). The intent is to make the full, distributed, permanent cost of
conversion legible — and to refuse the framing that nature is for sale.

---

## References

- de Groot, R. et al. (2012). *Global estimates of the value of ecosystems and
  their services in monetary units.* Ecosystem Services 1(1): 50–61.
- Costanza, R. et al. (2014). *Changes in the global value of ecosystem services.*
  Global Environmental Change 26: 152–158.
- Pan, Y. et al. (2011). *A Large and Persistent Carbon Sink in the World's
  Forests.* Science 333(6045): 988–993.
- IPCC AR6 WGIII (2022), Ch. 7 & Annex III.
- ESVD — Ecosystem Services Valuation Database (esvd.net).
