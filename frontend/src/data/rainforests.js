// Hardcoded Phase 1 overlays for the 4 major rainforest biomes.
// Polygons are deliberately coarse (illustrative footprints, not authoritative
// boundaries). Phase 3 ingests real WWF Terrestrial Ecoregions / GFW data.
//
// Each region carries display metadata used by the side panel. `areaSqm` are
// rounded order-of-magnitude footprints for the headline biome.

export const rainforests = [
  {
    id: 'amazon',
    name: 'Amazon Basin',
    region: 'Brazil, Peru, Colombia, Bolivia, Ecuador, Venezuela',
    areaSqm: 5.5e12, // ~5.5 million km²
    gdpCallout:
      'Standing, this basin generates more annual economic value than the entire cattle-ranching sector that drives its clearance in Brazil.',
    geojson: {
      type: 'Polygon',
      coordinates: [
        [
          [-73, 5],
          [-50, 5],
          [-44, -2],
          [-50, -12],
          [-65, -16],
          [-75, -10],
          [-78, -2],
          [-73, 5],
        ],
      ],
    },
  },
  {
    id: 'congo',
    name: 'Congo Basin',
    region: 'DRC, Republic of Congo, Cameroon, Gabon',
    areaSqm: 3.7e12, // ~3.7 million km²
    gdpCallout:
      'Standing, this basin generates more annual economic value than the timber-export industry that threatens it across Central Africa.',
    geojson: {
      type: 'Polygon',
      coordinates: [
        [
          [8, 4],
          [27, 5],
          [30, -2],
          [27, -8],
          [18, -6],
          [10, -3],
          [8, 4],
        ],
      ],
    },
  },
  {
    id: 'southeast-asia',
    name: 'Southeast Asian Rainforests',
    region: 'Indonesia, Malaysia, Papua New Guinea, Borneo',
    areaSqm: 2.5e12, // ~2.5 million km²
    gdpCallout:
      'Standing, these forests generate more annual economic value than the palm-oil plantations replacing them across the region.',
    geojson: {
      type: 'MultiPolygon',
      coordinates: [
        [
          [
            [109, 4],
            [119, 4],
            [118, -4],
            [110, -3],
            [109, 4],
          ],
        ],
        [
          [
            [95, 6],
            [106, -2],
            [114, -8],
            [141, -8],
            [141, 0],
            [120, 2],
            [100, 7],
            [95, 6],
          ],
        ],
      ],
    },
  },
  {
    id: 'central-america',
    name: 'Central American Rainforests',
    region: 'Costa Rica, Panama',
    areaSqm: 6.0e10, // ~60,000 km²
    gdpCallout:
      'Standing, these forests generate more annual economic value than the agricultural conversion pressuring them in the isthmus.',
    geojson: {
      type: 'Polygon',
      coordinates: [
        [
          [-86, 11],
          [-82, 11],
          [-77, 9],
          [-80, 7],
          [-85, 8.5],
          [-86, 11],
        ],
      ],
    },
  },
]
