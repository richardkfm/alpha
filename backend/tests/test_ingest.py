"""Tests for the Phase 3 ingestion CLI (``ingest.py``)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ingest  # noqa: E402  (regression: this import used to raise ImportError)


def test_validate_passes_on_the_bundled_datasets(capsys):
    assert ingest.main(["validate"]) == 0
    out = capsys.readouterr().out
    # Both the RESOLVE ecoregions and the curated seeds are checked.
    assert "ecoregions.geojson" in out
    assert "wwf_biomes.geojson" in out
    assert "OK" in out


def test_classify_prints_the_detected_biome(capsys):
    assert ingest.main(["classify", "-62", "-4"]) == 0
    assert json.loads(capsys.readouterr().out)["biome_key"] == "tropical_rainforest"


def test_classify_rejects_non_numeric_coordinates(capsys):
    assert ingest.main(["classify", "west", "south"]) == 2
    assert "usage" in capsys.readouterr().err
