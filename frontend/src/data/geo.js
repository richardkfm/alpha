// alpha — small GeoJSON geometry helpers (dependency-free).
//
// Used to place value "bubbles" / heat points at a region's centre without a
// backend round-trip. These are display-only approximations (a vertex mean of
// the largest ring), not survey-grade centroids.

// Average [lng, lat] of a single linear ring, ignoring the closing duplicate
// vertex when present.
function ringMean(ring) {
  const n =
    ring.length > 1 &&
    ring[0][0] === ring[ring.length - 1][0] &&
    ring[0][1] === ring[ring.length - 1][1]
      ? ring.length - 1
      : ring.length
  let lng = 0
  let lat = 0
  for (let i = 0; i < n; i++) {
    lng += ring[i][0]
    lat += ring[i][1]
  }
  return { lng: lng / n, lat: lat / n, n }
}

// Rough planar area of a ring (shoelace) — only used to pick the largest part
// of a MultiPolygon, so degree-space is fine.
function ringArea(ring) {
  let a = 0
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    a += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1]
  }
  return Math.abs(a) / 2
}

// Representative [lng, lat] for a Polygon or MultiPolygon geometry.
export function centroid(geometry) {
  if (!geometry) return null
  if (geometry.type === 'Polygon') {
    return toLngLat(ringMean(geometry.coordinates[0]))
  }
  if (geometry.type === 'MultiPolygon') {
    // centre of the largest constituent polygon's outer ring
    let best = null
    let bestArea = -1
    for (const poly of geometry.coordinates) {
      const outer = poly[0]
      const area = ringArea(outer)
      if (area > bestArea) {
        bestArea = area
        best = outer
      }
    }
    return best ? toLngLat(ringMean(best)) : null
  }
  return null
}

function toLngLat({ lng, lat }) {
  return [lng, lat]
}
