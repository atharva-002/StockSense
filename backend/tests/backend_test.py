"""StockSense backend API tests."""
import os
import math
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Health ----------
def test_health(client):
    r = client.get(f"{API}/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("app") == "StockSense"
    assert data.get("status") == "ok"
    assert isinstance(data.get("model_version"), str)
    assert data.get("horizon") == 28


# ---------- Catalog ----------
def test_catalog(client):
    r = client.get(f"{API}/catalog")
    assert r.status_code == 200
    data = r.json()
    assert sorted(data["stores"]) == list(range(1, 11))
    assert sorted(data["items"]) == list(range(1, 11))
    assert "pairs" in data
    assert len(data["pairs"]) == 100


# ---------- EDA ----------
def test_eda(client):
    r = client.get(f"{API}/eda")
    assert r.status_code == 200
    d = r.json()
    for k in ("monthly_trend", "weekly_seasonality", "yearly_seasonality"):
        assert k in d and len(d[k]) > 0


# ---------- Models ----------
def test_models(client):
    r = client.get(f"{API}/models")
    assert r.status_code == 200
    d = r.json()
    assert len(d["comparison"]) == 3
    assert d["best_model"] == "lightgbm"
    assert "cv_folds" in d
    assert isinstance(d.get("improvement_over_naive_pct"), (int, float))


# ---------- Forecast ----------
def test_forecast(client):
    r = client.get(f"{API}/forecast", params={"store": 1, "item": 1, "horizon": 14})
    assert r.status_code == 200
    d = r.json()
    assert len(d["history_dates"]) == 180
    assert len(d["forecast_mean"]) == 14
    for lo, hi in zip(d["forecast_lower"], d["forecast_upper"]):
        assert lo <= hi


# ---------- Explain ----------
def test_explain(client):
    r = client.get(f"{API}/explain", params={"store": 1, "item": 1})
    assert r.status_code == 200
    d = r.json()
    assert "global_importance" in d and len(d["global_importance"]) > 0
    assert "local_drivers" in d


# ---------- Inventory ----------
def test_inventory_basic(client):
    r = client.get(f"{API}/inventory", params={"store": 1, "item": 1, "lead_time": 7, "service_level": 0.95})
    assert r.status_code == 200
    d = r.json()
    assert d["reorder_point"] >= d["safety_stock"]
    assert "order_quantity" in d
    assert d["stockout_risk"] in ("low", "medium", "high")


def test_inventory_leadtime_sqrt(client):
    r1 = client.get(f"{API}/inventory", params={"store": 1, "item": 1, "lead_time": 4, "service_level": 0.95}).json()
    r2 = client.get(f"{API}/inventory", params={"store": 1, "item": 1, "lead_time": 16, "service_level": 0.95}).json()
    # sqrt(16)/sqrt(4) = 2
    ratio = r2["safety_stock"] / max(r1["safety_stock"], 1e-6)
    assert 1.7 <= ratio <= 2.3, f"Expected ~2x safety stock, got ratio={ratio}"


def test_inventory_service_level_monotonic(client):
    r1 = client.get(f"{API}/inventory", params={"store": 1, "item": 1, "lead_time": 7, "service_level": 0.90}).json()
    r2 = client.get(f"{API}/inventory", params={"store": 1, "item": 1, "lead_time": 7, "service_level": 0.99}).json()
    assert r2["safety_stock"] > r1["safety_stock"]


def test_inventory_alerts(client):
    r = client.get(f"{API}/inventory/alerts")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 100
    alerts = d["alerts"]
    assert len(alerts) > 0
    # Check sorted by risk (high > medium > low)
    rank = {"high": 3, "medium": 2, "low": 1}
    ranks = [rank.get(a.get("stockout_risk", "low"), 0) for a in alerts]
    assert ranks == sorted(ranks, reverse=True)


# ---------- Drift ----------
def test_drift(client):
    r = client.get(f"{API}/drift")
    assert r.status_code == 200
    d = r.json()
    assert d["overall_status"] in ("OK", "WARNING", "DRIFT")
    assert isinstance(d["features"], list) and len(d["features"]) > 0
    assert "recommendation" in d


# ---------- Model card ----------
def test_model_card(client):
    r = client.get(f"{API}/model-card")
    assert r.status_code == 200
    d = r.json()
    for k in ("name", "version", "features", "metrics"):
        assert k in d
