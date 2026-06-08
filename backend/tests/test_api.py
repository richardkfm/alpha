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


def test_regions_returns_valued_catalogue():
    res = client.get("/api/v1/regions")
    assert res.status_code == 200
    body = res.json()
    assert body["currency"] == "USD"
    regions = body["regions"]
    # Many more than the original 4 hardcoded overlays, spanning all five biomes.
    assert len(regions) >= 20
    assert {r["biome_key"] for r in regions} == {
        "tropical_rainforest",
        "temperate_forest",
        "mangrove",
        "wetland",
        "temperate_grassland",
    }
    amazon = next(r for r in regions if r["id"] == "amazon")
    assert amazon["total_ecosystem_value_per_year"] > 0
    assert amazon["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert body["dataset"]["count"] == len(regions)


def test_datasets_catalogue():
    res = client.get("/api/v1/datasets")
    assert res.status_code == 200
    body = res.json()
    assert body["domains"] and body["needs"]
    ids = {d["id"] for d in body["domains"]}
    assert {"biome_boundaries", "esv_reference", "carbon_price", "fx_rates"} <= ids
    for d in body["domains"]:
        assert d["status"] in ("authoritative", "reference", "placeholder")
        assert d["sources"] and "label" in d
    # roadmap entries describe a current -> planned upgrade
    assert all({"current", "planned", "why"} <= n.keys() for n in body["needs"])


def test_regions_respects_currency():
    usd = client.get("/api/v1/regions").json()["regions"]
    brl = client.get("/api/v1/regions?currency=BRL").json()["regions"]
    usd_amazon = next(r for r in usd if r["id"] == "amazon")
    brl_amazon = next(r for r in brl if r["id"] == "amazon")
    assert brl_amazon["currency"] == "BRL"
    # BRL reference rate is > 1 per USD, so the BRL total must be larger.
    assert brl_amazon["total_ecosystem_value_per_year"] > usd_amazon[
        "total_ecosystem_value_per_year"
    ]
