"""alpha — Phase 3 ingestion CLI.

A small, dependency-free command-line entry point for the data-ingestion layer.

Commands:
  validate   Check the bundled biome-boundary dataset is well-formed and that every
             feature maps to a known valuation biome. Runs fully offline (CI-safe).
  classify   Classify a single "lon lat" coordinate against the boundaries.
  refresh    Print the documented procedure for regenerating the boundary seed from
             the authoritative WWF / Copernicus sources (the full datasets need
             network access and GIS tooling, so this command documents rather than
             silently downloads). See backend/INGESTION.md.

Usage:
  python ingest.py validate
  python ingest.py classify -62 -4
  python ingest.py refresh
"""
from __future__ import annotations

import json
import sys

from biome_classifier import DATA_PATH, _load_boundaries, classify_point
from reference_data import BIOMES

REFRESH_SOURCES = [
    ("WWF Terrestrial Ecoregions of the World (TEOW / Olson et al. 2001)",
     "https://www.worldwildlife.org/publications/terrestrial-ecoregions-of-the-world"),
    ("Copernicus Global Land Service — Land Cover 100m, collection 3 (CGLS-LC100)",
     "https://doi.org/10.5281/zenodo.3939050"),
    ("Global Mangrove Watch (mangrove extent)",
     "https://www.globalmangrovewatch.org/"),
    ("Ramsar Sites Information Service (inland wetlands)",
     "https://rsis.ramsar.org/"),
]


def cmd_validate() -> int:
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        fc = json.load(fh)
    features = fc.get("features", [])
    errors: list[str] = []
    counts: dict[str, int] = {}
    for i, feat in enumerate(features):
        key = feat.get("properties", {}).get("biome_key")
        if key not in BIOMES:
            errors.append(f"feature {i}: unknown biome_key {key!r}")
            continue
        geom = feat.get("geometry", {})
        if geom.get("type") not in ("Polygon", "MultiPolygon") or not geom.get("coordinates"):
            errors.append(f"feature {i} ({key}): missing/invalid geometry")
            continue
        counts[key] = counts.get(key, 0) + 1

    print(f"dataset: {DATA_PATH}")
    print(f"features: {len(features)}  polygons: {len(_load_boundaries())}")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]} feature(s)")
    missing = sorted(set(BIOMES) - set(counts))
    if missing:
        print(f"note: no boundary coverage yet for: {', '.join(missing)}")
    if errors:
        print("\nVALIDATION ERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK — dataset is well-formed.")
    return 0


def cmd_classify(args: list[str]) -> int:
    if len(args) != 2:
        print("usage: python ingest.py classify <lon> <lat>", file=sys.stderr)
        return 2
    lon, lat = float(args[0]), float(args[1])
    print(json.dumps(classify_point(lon, lat), indent=2))
    return 0


def cmd_refresh() -> int:
    print("Refreshing the biome-boundary seed (manual procedure)\n")
    print("The authoritative datasets are large and require network access plus GIS")
    print("tooling (geopandas / GDAL); they are intentionally not vendored. To")
    print("regenerate data/wwf_biomes.geojson:\n")
    print("  1. Download the source layers:")
    for name, url in REFRESH_SOURCES:
        print(f"       - {name}\n         {url}")
    print("  2. Dissolve TEOW ecoregions to the WWF biome class, then map each class")
    print("     to one of alpha's five valuation biomes (see backend/INGESTION.md).")
    print("  3. Simplify geometries (e.g. mapshaper, 1-5 km tolerance) and export as")
    print("     GeoJSON with a `biome_key` property per feature.")
    print("  4. Run `python ingest.py validate` to confirm the result.")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "validate":
        return cmd_validate()
    if cmd == "classify":
        return cmd_classify(rest)
    if cmd == "refresh":
        return cmd_refresh()
    print(f"unknown command: {cmd}\n", file=sys.stderr)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
