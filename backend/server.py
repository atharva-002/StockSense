"""StockSense FastAPI backend.

Loads precomputed artefacts from backend/artifacts at startup — no training on the server.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

ARTIFACTS_DIR = ROOT_DIR / "artifacts"


class Artifacts:
    """Lazy container for all precomputed JSON + model objects."""

    def __init__(self, base: Path):
        self.base = base
        self.catalog: dict[str, Any] = {}
        self.eda: dict[str, Any] = {}
        self.metrics: dict[str, Any] = {}
        self.forecasts: dict[str, Any] = {}
        self.shap: dict[str, Any] = {}
        self.experiments: dict[str, Any] = {}
        self.model_card: dict[str, Any] = {}
        self.drift: dict[str, Any] = {}
        self.loaded = False

    def load(self) -> None:
        def _read(name: str, default):
            p = self.base / name
            if not p.exists():
                return default
            with open(p) as f:
                return json.load(f)

        self.catalog = _read("catalog.json", {"stores": [], "items": [], "pairs": [], "model_version": "n/a", "horizon": 28})
        self.eda = _read("eda.json", {})
        self.metrics = _read("metrics.json", {})
        self.forecasts = _read("forecasts.json", {})
        self.shap = _read("shap.json", {"global": [], "examples": []})
        self.experiments = _read("experiments.json", {"runs": []})
        self.model_card = _read("model_card.json", {})
        self.drift = _read("drift_report.json", {
            "overall_status": "OK",
            "retrain_recommended": False,
            "recommendation": "No drift data available (drift job has not run).",
            "n_features_checked": 0,
            "features": [],
        })
        self.loaded = True


ART = Artifacts(ARTIFACTS_DIR)

app = FastAPI(title="StockSense API", version="1.0.0")
api_router = APIRouter(prefix="/api")


@app.on_event("startup")
def _load_artifacts() -> None:
    ART.load()


# ------------------------- Routes -------------------------
@api_router.get("/")
def root() -> dict:
    return {
        "app": "StockSense",
        "status": "ok",
        "model_version": ART.catalog.get("model_version", "n/a"),
        "horizon": ART.catalog.get("horizon", 28),
        "n_stores": len(ART.catalog.get("stores", [])),
        "n_items": len(ART.catalog.get("items", [])),
    }


@api_router.get("/catalog")
def catalog() -> dict:
    return ART.catalog


@api_router.get("/eda")
def eda() -> dict:
    if not ART.eda:
        raise HTTPException(503, "EDA artefact not loaded")
    return ART.eda


@api_router.get("/models")
def models() -> dict:
    if not ART.metrics:
        raise HTTPException(503, "Metrics artefact not loaded")
    return ART.metrics


@api_router.get("/experiments")
def experiments() -> dict:
    return ART.experiments


@api_router.get("/forecast")
def forecast(store: int, item: int, horizon: int = 28) -> dict:
    key = f"{store}_{item}"
    f = ART.forecasts.get(key)
    if not f:
        raise HTTPException(404, f"No forecast for store={store}, item={item}")
    h = max(1, min(int(horizon), len(f["forecast_mean"])))
    return {
        "store": store, "item": item, "horizon": h,
        "history_dates": f["history_dates"],
        "history_sales": f["history_sales"],
        "forecast_dates": f["forecast_dates"][:h],
        "forecast_mean": f["forecast_mean"][:h],
        "forecast_lower": f["forecast_lower"][:h],
        "forecast_upper": f["forecast_upper"][:h],
        "model_version": ART.catalog.get("model_version", "n/a"),
    }


@api_router.get("/explain")
def explain(store: int, item: int) -> dict:
    glob = ART.shap.get("global", [])
    ex_list = ART.shap.get("examples", [])
    # Prefer an example matching the requested series; else first available.
    chosen: Optional[dict] = next(
        (e for e in ex_list if e.get("store") == store and e.get("item") == item), None
    )
    if chosen is None and ex_list:
        chosen = ex_list[0]
    return {
        "store": store, "item": item,
        "global_importance": glob[:15],
        "local_drivers": chosen["drivers"] if chosen else [],
        "note": "SHAP computed offline during training; the API does not depend on shap at runtime.",
    }


@api_router.get("/inventory")
def inventory(
    store: int,
    item: int,
    lead_time: int = 7,
    service_level: float = 0.95,
    review_period: int = 14,
    on_hand: float = 0.0,
) -> dict:
    from inventory import compute_inventory

    key = f"{store}_{item}"
    f = ART.forecasts.get(key)
    if not f:
        raise HTTPException(404, f"No forecast for store={store}, item={item}")
    res = compute_inventory(
        forecast_mean=f["forecast_mean"],
        forecast_upper=f["forecast_upper"],
        forecast_lower=f["forecast_lower"],
        lead_time_days=lead_time,
        service_level=service_level,
        review_period_days=review_period,
        on_hand=on_hand,
    )
    return {"store": store, "item": item, **res.to_dict()}


@api_router.get("/inventory/alerts")
def inventory_alerts(lead_time: int = 7, service_level: float = 0.95, top_n: int = 15) -> dict:
    from inventory import compute_inventory

    rows = []
    for key, f in ART.forecasts.items():
        store, item = (int(x) for x in key.split("_"))
        try:
            r = compute_inventory(
                f["forecast_mean"], f["forecast_upper"], f["forecast_lower"],
                lead_time_days=lead_time, service_level=service_level,
            )
        except Exception:
            continue
        rows.append({
            "store": store, "item": item,
            "mean_daily_demand": round(r.mean_daily_demand, 2),
            "reorder_point": round(r.reorder_point, 2),
            "safety_stock": round(r.safety_stock, 2),
            "order_quantity": round(r.order_quantity, 2),
            "stockout_risk": r.stockout_risk,
        })
    risk_order = {"high": 0, "medium": 1, "low": 2}
    rows.sort(key=lambda r: (risk_order.get(r["stockout_risk"], 3), -r["reorder_point"]))
    return {"lead_time": lead_time, "service_level": service_level, "alerts": rows[:top_n], "total": len(rows)}


@api_router.get("/drift")
def drift() -> dict:
    return ART.drift


@api_router.get("/model-card")
def model_card() -> dict:
    return ART.model_card


app.include_router(api_router)


# CORS
origins = os.environ.get("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins.split(",")] if origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
