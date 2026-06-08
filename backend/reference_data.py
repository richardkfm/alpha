"""alpha — Phase 2 valuation reference data.

Documented reference values and citations for the Total Ecosystem Value (TEV)
engine. Every figure here is a biome-level reference estimate drawn from the
peer-reviewed ecosystem-services literature, not a live measurement. Phase 3
replaces the static biome lookup with real land-cover classification, and
Phase 4 wires the FX rates to a live feed.

Primary sources
---------------
- de Groot, R. et al. (2012). "Global estimates of the value of ecosystems and
  their services in monetary units." *Ecosystem Services* 1(1): 50-61. — the
  per-biome, per-service USD/ha/yr reference values underpinning the Ecosystem
  Services Valuation Database (ESVD).
- Costanza, R. et al. (2014). "Changes in the global value of ecosystem
  services." *Global Environmental Change* 26: 152-158. — cross-check on biome
  aggregates.
- Pan, Y. et al. (2011). "A Large and Persistent Carbon Sink in the World's
  Forests." *Science* 333(6045): 988-993. — net carbon sequestration rates of
  intact forest.
- IPCC AR6 WGIII (2022), Ch. 7 & Annex III. — carbon price ranges consistent
  with sub-2 °C pathways (used to anchor the reference carbon price).

All monetary reference values are expressed in USD per hectare per year and
converted to USD per square metre per year (÷ 10,000) by the engine. See
`backend/METHODOLOGY.md` for the full derivation of each category.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Carbon price (USD per tonne CO2-equivalent).
#
# A single transparent reference price applied to every biome's sequestration
# rate. $30/tCO2 sits between voluntary nature-based credit prices (~$10-15) and
# central social-cost-of-carbon / compliance estimates ($50+), and is within the
# IPCC AR6 WGIII range for 2030 mitigation pathways. Phase 4 connects to live
# carbon-market data.
# ---------------------------------------------------------------------------
CARBON_PRICE_USD_PER_TCO2 = 30.0

# Hectare -> square metre.
SQM_PER_HECTARE = 10_000.0


# ---------------------------------------------------------------------------
# Biome reference table.
#
# For each biome:
#   - sequestration_tco2_ha_yr: net CO2 sequestered per hectare per year
#     (Pan et al. 2011 and blue-carbon literature for mangroves/wetlands).
#     Carbon Capture Yield = sequestration_tco2_ha_yr * CARBON_PRICE_USD_PER_TCO2.
#   - the remaining four categories are reference USD/ha/yr values mapped from the
#     de Groot et al. (2012) / ESVD service groups:
#       climate_regulation  <- climate regulation (evapotranspiration cooling,
#                              excluding the carbon already counted above)
#       water_filtration    <- water purification + flow regulation
#       biodiversity_premium<- genetic resources + habitat/refugia services
#       soil_nutrient_value <- erosion prevention + soil-fertility maintenance
#
# Values are deliberately conservative (lower-to-mid of published ranges).
# ---------------------------------------------------------------------------
BIOMES: dict[str, dict] = {
    "tropical_rainforest": {
        "label": "Tropical Rainforest",
        "sequestration_tco2_ha_yr": 2.3,   # Pan et al. 2011 (intact tropical sink)
        "climate_regulation_usd_ha_yr": 360.0,
        "water_filtration_usd_ha_yr": 200.0,
        "biodiversity_premium_usd_ha_yr": 500.0,
        "soil_nutrient_value_usd_ha_yr": 120.0,
    },
    "temperate_forest": {
        "label": "Temperate Forest",
        "sequestration_tco2_ha_yr": 1.5,
        "climate_regulation_usd_ha_yr": 250.0,
        "water_filtration_usd_ha_yr": 150.0,
        "biodiversity_premium_usd_ha_yr": 250.0,
        "soil_nutrient_value_usd_ha_yr": 100.0,
    },
    "mangrove": {
        "label": "Mangrove",
        "sequestration_tco2_ha_yr": 6.0,   # blue carbon; high per-ha burial rate
        "climate_regulation_usd_ha_yr": 500.0,
        "water_filtration_usd_ha_yr": 900.0,
        "biodiversity_premium_usd_ha_yr": 800.0,
        "soil_nutrient_value_usd_ha_yr": 300.0,
    },
    "wetland": {
        "label": "Inland Wetland",
        "sequestration_tco2_ha_yr": 1.0,
        "climate_regulation_usd_ha_yr": 400.0,
        "water_filtration_usd_ha_yr": 3000.0,  # ESVD: water services dominate wetlands
        "biodiversity_premium_usd_ha_yr": 1200.0,
        "soil_nutrient_value_usd_ha_yr": 250.0,
    },
    "temperate_grassland": {
        "label": "Temperate Grassland",
        "sequestration_tco2_ha_yr": 0.5,
        "climate_regulation_usd_ha_yr": 80.0,
        "water_filtration_usd_ha_yr": 60.0,
        "biodiversity_premium_usd_ha_yr": 120.0,
        "soil_nutrient_value_usd_ha_yr": 200.0,
    },
    # --- "ordinary" and smaller resources (de Groot et al. 2012 ESVD groups:
    # boreal/woodland forest, cropland, lakes & rivers, urban green). Regulating
    # + supporting services only — provisioning (e.g. crop yield, drinking-water
    # supply revenue) is deliberately excluded, so these reflect the value that is
    # *lost* when the land is sealed/converted, not its market output. ---
    "boreal_forest": {
        "label": "Boreal Forest (Taiga)",
        "sequestration_tco2_ha_yr": 1.2,   # slower growth, vast soil/peat carbon store
        "climate_regulation_usd_ha_yr": 180.0,
        "water_filtration_usd_ha_yr": 120.0,
        "biodiversity_premium_usd_ha_yr": 150.0,
        "soil_nutrient_value_usd_ha_yr": 150.0,
    },
    "cropland": {
        "label": "Cropland & Agriculture",
        "sequestration_tco2_ha_yr": 0.3,   # managed soils; modest net regulating sink
        "climate_regulation_usd_ha_yr": 60.0,
        "water_filtration_usd_ha_yr": 40.0,
        "biodiversity_premium_usd_ha_yr": 50.0,
        "soil_nutrient_value_usd_ha_yr": 180.0,  # the soil itself is farmland's key asset
    },
    "freshwater": {
        "label": "Freshwater (Lakes & Rivers)",
        "sequestration_tco2_ha_yr": 0.0,   # open water: negligible net sequestration
        "climate_regulation_usd_ha_yr": 300.0,
        "water_filtration_usd_ha_yr": 3500.0,  # ESVD: water supply + purification dominate
        "biodiversity_premium_usd_ha_yr": 600.0,
        "soil_nutrient_value_usd_ha_yr": 0.0,    # no soil column
    },
    "peri_urban": {
        "label": "Peri-urban / Managed Open Land",
        "sequestration_tco2_ha_yr": 0.6,
        "climate_regulation_usd_ha_yr": 150.0,  # local cooling near built-up areas
        "water_filtration_usd_ha_yr": 120.0,    # stormwater infiltration
        "biodiversity_premium_usd_ha_yr": 90.0,
        "soil_nutrient_value_usd_ha_yr": 120.0,
    },
}

DEFAULT_BIOME = "tropical_rainforest"

# Order in which yield categories are reported (matches the product spec).
YIELD_CATEGORIES = (
    "carbon_capture",
    "climate_regulation",
    "water_filtration",
    "biodiversity_premium",
    "soil_nutrient_value",
)


# ---------------------------------------------------------------------------
# Currency conversion.
#
# Indicative reference rates relative to USD (base), as of 2025-12. These are
# static placeholders so the API can offer a USD / EUR / BRL toggle today;
# Phase 4 connects to a live FX source.
# ---------------------------------------------------------------------------
FX_AS_OF = "2025-12"

CURRENCIES: dict[str, dict] = {
    "USD": {"label": "US Dollar", "symbol": "$", "rate_per_usd": 1.0},
    "EUR": {"label": "Euro", "symbol": "€", "rate_per_usd": 0.92},
    "BRL": {"label": "Brazilian Real", "symbol": "R$", "rate_per_usd": 5.40},
}

DEFAULT_CURRENCY = "USD"


def biome_per_sqm_usd(biome_key: str, carbon_price: float | None = None) -> dict[str, float]:
    """Return the 5 reference yields for a biome, in USD per sqm per year.

    Carbon is derived from the biome's sequestration rate and a carbon price; the
    other four are converted from USD/ha/yr to USD/sqm/yr. ``carbon_price``
    defaults to the static reference (``CARBON_PRICE_USD_PER_TCO2``); the API layer
    may inject a live market price (see ``live_data.py``).
    """
    b = BIOMES[biome_key]
    price = CARBON_PRICE_USD_PER_TCO2 if carbon_price is None else carbon_price
    carbon_usd_ha_yr = b["sequestration_tco2_ha_yr"] * price
    return {
        "carbon_capture": carbon_usd_ha_yr / SQM_PER_HECTARE,
        "climate_regulation": b["climate_regulation_usd_ha_yr"] / SQM_PER_HECTARE,
        "water_filtration": b["water_filtration_usd_ha_yr"] / SQM_PER_HECTARE,
        "biodiversity_premium": b["biodiversity_premium_usd_ha_yr"] / SQM_PER_HECTARE,
        "soil_nutrient_value": b["soil_nutrient_value_usd_ha_yr"] / SQM_PER_HECTARE,
    }
