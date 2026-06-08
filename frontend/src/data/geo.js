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

// Build a small square polygon (~`half`° per side) around a [lng, lat] point so a
// single coordinate still has an area to value.
function squareAround(lng, lat, half = 0.05) {
  return {
    type: 'Polygon',
    coordinates: [[
      [lng - half, lat - half],
      [lng + half, lat - half],
      [lng + half, lat + half],
      [lng - half, lat + half],
      [lng - half, lat - half],
    ]],
  }
}

// Parse free-text search input into a GeoJSON geometry + a human label.
// Accepts: a GeoJSON geometry / Feature / FeatureCollection (JSON), a
// "lat, lng" point, or a "west, south, east, north" bounding box.
// Throws an Error with a user-facing message on bad input.
export function parseAreaInput(raw) {
  const text = (raw || '').trim()
  if (!text) throw new Error('Enter coordinates or paste a GeoJSON polygon.')

  if (text[0] === '{') {
    let obj
    try {
      obj = JSON.parse(text)
    } catch (e) {
      throw new Error('That looks like JSON but could not be parsed.')
    }
    let geom = obj
    if (obj.type === 'Feature') geom = obj.geometry
    else if (obj.type === 'FeatureCollection') geom = obj.features?.[0]?.geometry
    if (geom && (geom.type === 'Polygon' || geom.type === 'MultiPolygon') && geom.coordinates) {
      return { geometry: geom, label: 'Custom polygon' }
    }
    throw new Error('Paste a GeoJSON Polygon or MultiPolygon (or a Feature wrapping one).')
  }

  const nums = text.split(/[\s,]+/).map(Number).filter((n) => !Number.isNaN(n))
  if (nums.length === 2) {
    const [lat, lng] = nums // geographic convention: latitude first
    if (Math.abs(lat) > 90 || Math.abs(lng) > 180) {
      throw new Error('Point out of range — expected "lat, lng".')
    }
    return { geometry: squareAround(lng, lat), label: `Point ${lat}, ${lng}` }
  }
  if (nums.length === 4) {
    const [w, s, e, n] = nums
    return {
      geometry: {
        type: 'Polygon',
        coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
      },
      label: 'Bounding box',
    }
  }
  throw new Error('Enter "lat, lng", a "w, s, e, n" box, or paste a GeoJSON polygon.')
}
