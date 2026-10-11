"""Smoke test the FastAPI app against precomputed artefacts."""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "backend" / "artifacts"


@pytest.fixture(scope="module")
def client():
    if not (ART / "catalog.json").exists():
        pytest.skip("artifacts not built; run `make train` first")
    os.chdir(ROOT / "backend")
    import server as srv  # imports local backend/server.py
    from fastapi.testclient import TestClient
    srv.ART.load()
    return TestClient(srv.app)


def test_health(client):
    r = client.get("/api/")
    assert r.status_code == 200
    assert r.json()["app"] == "StockSense"


def test_models(client):
    r = client.get("/api/models")
    assert r.status_code == 200
    data = r.json()
    assert "comparison" in data
    assert data["best_model"]


def test_eda(client):
    r = client.get("/api/eda")
    assert r.status_code == 200
    assert "monthly_trend" in r.json()


def test_forecast(client):
    r = client.get("/api/forecast", params={"store": 1, "item": 1, "horizon": 14})
    assert r.status_code == 200
    body = r.json()
    assert len(body["forecast_mean"]) == 14
    for lo, hi in zip(body["forecast_lower"], body["forecast_upper"]):
        assert lo <= hi


def test_inventory(client):
    r = client.get(
        "/api/inventory",
        params={"store": 1, "item": 1, "lead_time": 7, "service_level": 0.95},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["safety_stock"] >= 0
    assert data["reorder_point"] >= data["safety_stock"]


def test_inventory_alerts(client):
    r = client.get("/api/inventory/alerts")
    assert r.status_code == 200
    assert "alerts" in r.json()


def test_drift(client):
    r = client.get("/api/drift")
    assert r.status_code == 200
    assert "overall_status" in r.json()


def test_explain(client):
    r = client.get("/api/explain", params={"store": 1, "item": 1})
    assert r.status_code == 200
    assert "global_importance" in r.json()
