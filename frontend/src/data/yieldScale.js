// alpha — cross-biome scale for service-yield bars.
//
// Bars encode *magnitude vs the richest biome*, not composition within a region:
// a service's bar fills relative to the strongest biome for that same service.
// This keeps a desert's biodiversity bar honestly short instead of pinned at
// 100% just because it's the largest of that biome's (uniformly small) services.
//
// The ceiling is derived from the live region catalogue — which spans every
// biome, including the richest (wetland biodiversity, freshwater water) — so the
// scale is real data in the same currency as the values it scales, not a guess.
import { YIELD_ROWS } from './yields.js'

// Floor so a tiny-but-nonzero yield still shows a sliver of bar.
const FLOOR_PCT = 2

// Per-service maximum across the catalogue, in the catalogue's current currency.
// `|| 1` guards against an empty catalogue (avoids divide-by-zero).
export function serviceCeilings(regions = []) {
  const ceilings = {}
  for (const { key } of YIELD_ROWS) {
    ceilings[key] =
      Math.max(0, ...regions.map((r) => r.yields_per_sqm_year?.[key] ?? 0)) || 1
  }
  return ceilings
}

// Bar width % for a value against its service ceiling, clamped to [FLOOR, 100].
// The clamp ceiling catches a fully-intact custom region that edges just above
// the catalogue's (intactness-scaled) reference biome.
export function barPct(value, ceiling) {
  const pct = ((value ?? 0) / (ceiling || 1)) * 100
  return Math.min(Math.max(pct, FLOOR_PCT), 100)
}
