"""API-level tests for the Phase 3 endpoints (FastAPI TestClient)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)

AMAZON = {
    "type": "Polygon",
    "coordinates": [[[-65, -5], [-60, -5], [-60, -2], [-65, -2], [-65, -5]]],
}


def test_valuation_auto_classifies_biome():
    res = client.post("/api/v1/valuation", json=AMAZON)
    assert res.status_code == 200
    body = res.json()
    assert body["classification"]["confidence"] == "matched"
    assert body["biome_key"] == "tropical_rainforest"
    assert body["classification"]["matched_region"] == "Amazon Basin"


def test_valuation_explicit_biome_wins():
    res = client.post("/api/v1/valuation?biome=mangrove", json=AMAZON)
    assert res.status_code == 200
    body = res.json()
    assert body["biome_key"] == "mangrove"
    assert body["classification"]["confidence"] == "explicit"


def test_classify_endpoint():
    res = client.post("/api/v1/classify", json=AMAZON)
    assert res.status_code == 200
    body = res.json()
    assert body["classification"]["biome_key"] == "tropical_rainforest"
    assert "primary" in body["boundary_dataset"]


def test_extract_esv_endpoint_deterministic():
    text = "Water purification was valued at US$3,000 per ha per year."
    res = client.post("/api/v1/extract-esv", json={"text": text, "backend": "deterministic"})
    assert res.status_code == 200
    body = res.json()
    assert body["backend"] == "deterministic"
    assert body["count"] == 1
    assert body["records"][0]["service"] == "water_filtration"
    assert body["records"][0]["value"] == 3000.0


def test_extract_esv_rejects_empty():
    res = client.post("/api/v1/extract-esv", json={"text": "   "})
    assert res.status_code == 422


def test_reference_still_works():
    res = client.get("/api/v1/reference")
    assert res.status_code == 200
    assert "tropical_rainforest" in res.json()["biomes"]
