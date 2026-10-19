import { describe, it, expect } from 'vitest'
import { centroid, parseAreaInput } from './geo.js'

describe('centroid', () => {
  it('is unchanged for an ordinary polygon', () => {
    const [lng, lat] = centroid({
      type: 'Polygon',
      coordinates: [[[-65, -5], [-60, -5], [-60, -2], [-65, -2], [-65, -5]]],
    })
    expect(lng).toBeCloseTo(-62.5, 9)
    expect(lat).toBeCloseTo(-3.5, 9)
  })

  it('stays on the antimeridian for a ring that crosses it', () => {
    // Fiji, 178E .. 179W: the plain vertex mean is -0.5, off West Africa.
    const [lng, lat] = centroid({
      type: 'Polygon',
      coordinates: [[[178, -19], [-179, -19], [-179, -16], [178, -16], [178, -19]]],
    })
    expect(Math.abs(Math.abs(lng) - 179.5)).toBeLessThan(1e-9)
    expect(lat).toBeCloseTo(-17.5, 9)
  })
})

describe('parseAreaInput', () => {
  it('tolerates a trailing separator', () => {
    expect(parseAreaInput('-3.1, -60.0,').label).toBe('Point -3.1, -60')
    expect(parseAreaInput('-65, -6, -60, -2,').label).toBe('Bounding box')
  })

  it('rejects input with non-numeric tokens instead of silently dropping them', () => {
    expect(() => parseAreaInput('12 abc 34')).toThrow()
    expect(() => parseAreaInput('-3.1, -60.0, x')).toThrow()
  })

  it('rejects an out-of-range bounding box', () => {
    expect(() => parseAreaInput('100, 200, 300, 400')).toThrow(/out of range/)
  })

  it('still parses the documented examples', () => {
    expect(parseAreaInput('-3.1, -60.0').geometry.type).toBe('Polygon')
    expect(parseAreaInput('-65, -6, -60, -2').geometry.coordinates[0][0]).toEqual([-65, -6])
  })
})
