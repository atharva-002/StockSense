"""StockSense training pipeline.

- Trains Seasonal Naive baseline + Linear baseline + LightGBM (global).
- Expanding-window time-based CV with 3 folds.
- Logs to MLflow (local file-based tracking).
- Computes SHAP global importance + a few per-forecast explanations OFFLINE.
- Produces 28-day forecast with prediction intervals (quantile LightGBM).
- Writes JSON + model.pkl into backend/artifacts/.
"""
from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from .features import FEATURE_COLS, LAGS, build_feature_frame
from .metrics import all_metrics

# ----- Config -----
HORIZON = 28
TEST_DAYS = 90  # last 3 months as hold-out test
CV_FOLDS = 3
CV_FOLD_DAYS = 60  # each fold validates on 60 consecutive days
RANDOM_SEED = 42
QUANTILES = [0.1, 0.5, 0.9]  # for prediction intervals


# ----------------------------------------------------------------------------
# Baselines
# ----------------------------------------------------------------------------
def seasonal_naive_forecast(df_train: pd.DataFrame, df_target_dates: pd.DataFrame) -> np.ndarray:
    """For each (store, item, date) in df_target_dates, use sales from exactly 364 days earlier."""
    lookup = (
        df_train.set_index(["store", "item", pd.to_datetime(df_train["date"])])["sales"].to_dict()
    )
    preds = []
    for _, row in df_target_dates.iterrows():
        key = (int(row["store"]), int(row["item"]), pd.Timestamp(row["date"]) - pd.Timedelta(days=364))
        v = lookup.get(key)
        if v is None:
            # Fallback: 7-day shift, else overall mean of same (store, item).
            key7 = (int(row["store"]), int(row["item"]), pd.Timestamp(row["date"]) - pd.Timedelta(days=7))
            v = lookup.get(key7)
            if v is None:
                v = df_train[(df_train["store"] == row["store"]) & (df_train["item"] == row["item"])]["sales"].mean()
        preds.append(v)
    return np.array(preds, dtype=float)


def linear_baseline_fit_predict(train_df, test_df, feature_cols):
    """Simple Ridge baseline on the same feature set."""
    m = Ridge(alpha=1.0, random_state=RANDOM_SEED)
    m.fit(train_df[feature_cols].values, train_df["sales"].values)
    return m.predict(test_df[feature_cols].values)


# ----------------------------------------------------------------------------
# Training
# ----------------------------------------------------------------------------
def train_lgb(train_df, feature_cols, params=None, num_boost_round=400, categorical=("store", "item")):
    params = params or {
        "objective": "regression",
        "metric": "rmse",
        "learning_rate": 0.08,
        "num_leaves": 63,
        "min_data_in_leaf": 50,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 5,
        "verbosity": -1,
        "seed": RANDOM_SEED,
    }
    dtrain = lgb.Dataset(train_df[feature_cols], label=train_df["sales"], categorical_feature=list(categorical))
    model = lgb.train(params, dtrain, num_boost_round=num_boost_round)
    return model


def train_lgb_quantile(train_df, feature_cols, quantile, num_boost_round=400, categorical=("store", "item")):
    params = {
        "objective": "quantile",
        "alpha": quantile,
        "metric": "quantile",
        "learning_rate": 0.08,
        "num_leaves": 63,
        "min_data_in_leaf": 50,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 5,
        "verbosity": -1,
        "seed": RANDOM_SEED,
    }
    dtrain = lgb.Dataset(train_df[feature_cols], label=train_df["sales"], categorical_feature=list(categorical))
    return lgb.train(params, dtrain, num_boost_round=num_boost_round)


# ----------------------------------------------------------------------------
# EDA
# ----------------------------------------------------------------------------
def compute_eda(df: pd.DataFrame) -> dict:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d["year_month"] = d["date"].dt.strftime("%Y-%m")
    d["dow"] = d["date"].dt.dayofweek
    d["month"] = d["date"].dt.month

    monthly = d.groupby("year_month")["sales"].sum().reset_index()
    monthly = monthly.sort_values("year_month")
    dow = d.groupby("dow")["sales"].mean().reset_index()
    monthly_season = d.groupby("month")["sales"].mean().reset_index()
    by_store = d.groupby("store")["sales"].sum().reset_index()
    by_item = d.groupby("item")["sales"].sum().reset_index()

    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return {
        "n_rows": int(len(d)),
        "date_range": [str(d["date"].min().date()), str(d["date"].max().date())],
        "n_stores": int(d["store"].nunique()),
        "n_items": int(d["item"].nunique()),
        "total_sales": int(d["sales"].sum()),
        "avg_daily_sales_overall": float(d.groupby("date")["sales"].sum().mean()),
        "monthly_trend": [
            {"period": r["year_month"], "sales": int(r["sales"])}
            for _, r in monthly.iterrows()
        ],
        "weekly_seasonality": [
            {"day": dow_names[int(r["dow"])], "avg_sales": round(float(r["sales"]), 2)}
            for _, r in dow.iterrows()
        ],
        "yearly_seasonality": [
            {"month": int(r["month"]), "avg_sales": round(float(r["sales"]), 2)}
            for _, r in monthly_season.iterrows()
        ],
        "sales_by_store": [
            {"store": int(r["store"]), "sales": int(r["sales"])}
            for _, r in by_store.sort_values("sales", ascending=False).iterrows()
        ],
        "sales_by_item": [
            {"item": int(r["item"]), "sales": int(r["sales"])}
            for _, r in by_item.sort_values("sales", ascending=False).iterrows()
        ],
    }


# ----------------------------------------------------------------------------
# Cross validation
# ----------------------------------------------------------------------------
def cv_evaluate(df_feats: pd.DataFrame, feature_cols: list[str], fold_days: int = CV_FOLD_DAYS, n_folds: int = CV_FOLDS):
    """Expanding-window CV. Returns per-fold metrics for naive, linear and lgb."""
    dates = pd.to_datetime(df_feats["date"])
    max_date = dates.max()
    folds_report = []

    # Define fold validation windows ending at max_date, going back.
    for fold_i in range(n_folds):
        val_end = max_date - pd.Timedelta(days=fold_days * fold_i)
        val_start = val_end - pd.Timedelta(days=fold_days - 1)
        train_end = val_start - pd.Timedelta(days=1)

        train_mask = dates <= train_end
        val_mask = (dates >= val_start) & (dates <= val_end)
        tr = df_feats[train_mask].dropna(subset=feature_cols)
        va = df_feats[val_mask].dropna(subset=feature_cols)
        if len(tr) < 100 or len(va) < 50:
            continue

        # Naive baseline from raw (we need the pre-feature frame for lookup — reconstruct from tr+va columns we have).
        full = pd.concat([tr, va])[["date", "store", "item", "sales"]]
        full_tr = full[full["date"] <= train_end]
        naive_preds = seasonal_naive_forecast(full_tr, va[["date", "store", "item"]])

        linear_preds = linear_baseline_fit_predict(tr, va, feature_cols)
        model = train_lgb(tr, feature_cols, num_boost_round=250)
        lgb_preds = model.predict(va[feature_cols].values)

        naive_m = all_metrics(va["sales"].values, naive_preds)
        linear_m = all_metrics(va["sales"].values, linear_preds)
        lgb_m = all_metrics(va["sales"].values, lgb_preds)

        folds_report.append({
            "fold": n_folds - fold_i,  # fold number ascending (oldest=1)
            "train_end": str(train_end.date()),
            "val_start": str(val_start.date()),
            "val_end": str(val_end.date()),
            "n_train": int(len(tr)),
            "n_val": int(len(va)),
            "naive": {k: round(v, 3) for k, v in naive_m.items()},
            "linear": {k: round(v, 3) for k, v in linear_m.items()},
            "lightgbm": {k: round(v, 3) for k, v in lgb_m.items()},
        })

    folds_report.sort(key=lambda r: r["fold"])
    return folds_report


# ----------------------------------------------------------------------------
# Per-series forecasting (recursive 28-day)
# ----------------------------------------------------------------------------
def generate_forecasts(df_raw: pd.DataFrame, median_model, lower_model, upper_model, horizon: int):
    """Recursive multi-step forecast per (store, item) using lag features.
    df_raw must have columns date, store, item, sales covering history up to 'origin'.
    """
    df = df_raw.copy()
    df["date"] = pd.to_datetime(df["date"])
    origin = df["date"].max()

    results = {}
    for (store, item), g in df.groupby(["store", "item"], sort=False):
        g = g.sort_values("date").reset_index(drop=True)
        history_sales = g["sales"].tolist()
        history_dates = g["date"].tolist()

        preds_mean, preds_low, preds_high, future_dates = [], [], [], []
        for h in range(1, horizon + 1):
            future_date = origin + pd.Timedelta(days=h)
            # Build feature row using history_sales + future_date.
            row = _build_one_feature_row(history_sales, history_dates, future_date, store, item)
            x = np.array([[row[c] for c in FEATURE_COLS]], dtype=float)
            med = float(median_model.predict(x)[0])
            lo = float(lower_model.predict(x)[0])
            hi = float(upper_model.predict(x)[0])
            med = max(0.0, med)
            lo = max(0.0, lo)
            hi = max(med, hi)
            preds_mean.append(med)
            preds_low.append(lo)
            preds_high.append(hi)
            future_dates.append(future_date)
            # Append to history for recursive lag reuse.
            history_sales.append(med)
            history_dates.append(future_date)

        results[(int(store), int(item))] = {
            "history_dates": [d.strftime("%Y-%m-%d") for d in g["date"].tolist()],
            "history_sales": g["sales"].astype(float).tolist(),
            "forecast_dates": [d.strftime("%Y-%m-%d") for d in future_dates],
            "forecast_mean": preds_mean,
            "forecast_lower": preds_low,
            "forecast_upper": preds_high,
        }
    return results


def _build_one_feature_row(history_sales, history_dates, future_date, store, item):
    """Compute lag/rolling features from history_sales for one future date."""
    hs = np.asarray(history_sales, dtype=float)
    n = len(hs)

    def lag(k):
        return float(hs[n - k]) if n - k >= 0 else float(hs.mean())

    def roll(w):
        tail = hs[max(0, n - w):n]
        return float(tail.mean()) if len(tail) else 0.0, float(tail.std(ddof=0)) if len(tail) else 0.0

    row = {
        "store": int(store),
        "item": int(item),
        "dayofweek": future_date.dayofweek,
        "day": future_date.day,
        "month": future_date.month,
        "year": future_date.year,
        "weekofyear": future_date.isocalendar().week,
        "quarter": future_date.quarter,
        "is_weekend": int(future_date.dayofweek >= 5),
        "is_holiday": int(future_date.strftime("%Y-%m-%d") in __import__("ml.features", fromlist=["US_HOLIDAYS"]).US_HOLIDAYS),
    }
    for k in LAGS:
        row[f"lag_{k}"] = lag(k)
    for w in (7, 14, 28):
        m, s = roll(w)
        row[f"rmean_{w}"] = m
        row[f"rstd_{w}"] = s
    return row


# ----------------------------------------------------------------------------
# SHAP (offline)
# ----------------------------------------------------------------------------
def compute_shap(model, X_sample: pd.DataFrame, feature_cols: list[str], max_examples: int = 10):
    try:
        import shap  # local import — training only
    except Exception as e:
        print(f"[train] shap unavailable, skipping: {e}")
        return {"global": [], "examples": []}
    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_sample[feature_cols])
    if isinstance(sv, list):
        sv = sv[0]
    importance = np.mean(np.abs(sv), axis=0)
    global_imp = [
        {"feature": c, "importance": round(float(v), 4)}
        for c, v in sorted(zip(feature_cols, importance), key=lambda t: -t[1])
    ]
    # A few per-forecast examples
    examples = []
    for i in range(min(max_examples, len(X_sample))):
        row_vals = sorted(
            [{"feature": c, "shap": round(float(sv[i, j]), 4), "value": round(float(X_sample[feature_cols].iloc[i, j]), 3)}
             for j, c in enumerate(feature_cols)],
            key=lambda t: -abs(t["shap"]),
        )[:10]
        examples.append({
            "store": int(X_sample["store"].iloc[i]),
            "item": int(X_sample["item"].iloc[i]),
            "drivers": row_vals,
        })
    return {"global": global_imp, "examples": examples}


# ----------------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------------
def run(data_path: str, out_dir: str, mlruns_dir: str, sample: bool = False) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"file:{mlruns_dir}")
    mlflow.set_experiment("stocksense")

    print(f"[train] loading {data_path}")
    df = pd.read_csv(data_path, parse_dates=["date"])
    if sample:
        # Smoke-test subset: keep 2 stores x 2 items.
        df = df[(df["store"] <= 2) & (df["item"] <= 2)]
        print(f"[train] SAMPLE mode: {df.shape}")

    print("[train] computing EDA")
    eda = compute_eda(df)
    with open(out / "eda.json", "w") as f:
        json.dump(eda, f, indent=2)

    print("[train] building features")
    feats = build_feature_frame(df)

    # Split: last TEST_DAYS as hold-out test.
    max_date = feats["date"].max()
    test_start = max_date - pd.Timedelta(days=TEST_DAYS - 1)
    train_mask = feats["date"] < test_start
    test_mask = feats["date"] >= test_start
    train_feats = feats[train_mask].dropna(subset=FEATURE_COLS)
    test_feats = feats[test_mask].dropna(subset=FEATURE_COLS)
    print(f"[train] train rows={len(train_feats)}, test rows={len(test_feats)}")

    with mlflow.start_run(run_name=f"stocksense-{int(time.time())}") as run:
        mlflow.log_param("horizon", HORIZON)
        mlflow.log_param("test_days", TEST_DAYS)
        mlflow.log_param("n_rows", len(df))

        # --------- Baselines on test ---------
        print("[train] evaluating seasonal naive on test")
        naive_preds = seasonal_naive_forecast(
            df[df["date"] < test_start], test_feats[["date", "store", "item"]]
        )
        naive_m = all_metrics(test_feats["sales"].values, naive_preds)

        print("[train] fitting Ridge baseline")
        linear_preds = linear_baseline_fit_predict(train_feats, test_feats, FEATURE_COLS)
        linear_m = all_metrics(test_feats["sales"].values, linear_preds)

        # --------- LightGBM ---------
        print("[train] fitting LightGBM median (0.5 quantile)")
        median_model = train_lgb_quantile(train_feats, FEATURE_COLS, 0.5, num_boost_round=400)
        print("[train] fitting LightGBM lower (0.1)")
        lower_model = train_lgb_quantile(train_feats, FEATURE_COLS, 0.1, num_boost_round=300)
        print("[train] fitting LightGBM upper (0.9)")
        upper_model = train_lgb_quantile(train_feats, FEATURE_COLS, 0.9, num_boost_round=300)

        lgb_preds = median_model.predict(test_feats[FEATURE_COLS].values)
        lgb_m = all_metrics(test_feats["sales"].values, lgb_preds)

        # Per store/item errors
        test_eval = test_feats[["store", "item", "sales"]].copy()
        test_eval["pred"] = lgb_preds
        test_eval["abs_err"] = (test_eval["sales"] - test_eval["pred"]).abs()
        by_store = test_eval.groupby("store").apply(
            lambda g: all_metrics(g["sales"].values, g["pred"].values)
        )
        by_item = test_eval.groupby("item").apply(
            lambda g: all_metrics(g["sales"].values, g["pred"].values)
        )
        by_store_item = test_eval.groupby(["store", "item"]).apply(
            lambda g: all_metrics(g["sales"].values, g["pred"].values)
        )

        def _nest(series):
            out_list = []
            for key, m in series.items():
                row = {"mape": round(m["mape"], 2), "rmse": round(m["rmse"], 2),
                       "mae": round(m["mae"], 2), "smape": round(m["smape"], 2)}
                if isinstance(key, tuple):
                    row["store"], row["item"] = int(key[0]), int(key[1])
                else:
                    row["key"] = int(key)
                out_list.append(row)
            return out_list

        comparison = [
            {"model": "seasonal_naive", **{k: round(v, 3) for k, v in naive_m.items()}},
            {"model": "ridge_baseline", **{k: round(v, 3) for k, v in linear_m.items()}},
            {"model": "lightgbm", **{k: round(v, 3) for k, v in lgb_m.items()}},
        ]
        best_model = min(comparison, key=lambda r: r["mape"])["model"]

        improvement_pct = round(
            (naive_m["mape"] - lgb_m["mape"]) / max(naive_m["mape"], 1e-9) * 100, 2
        )

        for row in comparison:
            mlflow.log_metric(f"{row['model']}_mape", row["mape"])
            mlflow.log_metric(f"{row['model']}_rmse", row["rmse"])

        # --------- Cross validation ---------
        print("[train] running expanding-window CV")
        cv_report = cv_evaluate(feats, FEATURE_COLS)

        # --------- SHAP ---------
        print("[train] computing SHAP (offline)")
        shap_sample = test_feats.sample(min(500, len(test_feats)), random_state=RANDOM_SEED)
        shap_report = compute_shap(median_model, shap_sample, FEATURE_COLS)

        # --------- Forecasts ---------
        print("[train] generating 28-day forecasts per (store, item)")
        # Use raw df (sales + date) through origin = max_date; features will be built recursively.
        forecasts = generate_forecasts(
            df.sort_values(["store", "item", "date"]).reset_index(drop=True),
            median_model, lower_model, upper_model, horizon=HORIZON,
        )
        # Trim history returned to UI to last 180 days.
        trimmed = {}
        for key, v in forecasts.items():
            hd, hs = v["history_dates"], v["history_sales"]
            if len(hd) > 180:
                hd = hd[-180:]
                hs = hs[-180:]
            trimmed[f"{key[0]}_{key[1]}"] = {
                "store": key[0], "item": key[1],
                "history_dates": hd, "history_sales": hs,
                "forecast_dates": v["forecast_dates"],
                "forecast_mean": [round(x, 2) for x in v["forecast_mean"]],
                "forecast_lower": [round(x, 2) for x in v["forecast_lower"]],
                "forecast_upper": [round(x, 2) for x in v["forecast_upper"]],
            }

        # --------- Save artefacts ---------
        model_version = time.strftime("%Y.%m.%d-%H%M%S")

        with open(out / "metrics.json", "w") as f:
            json.dump({
                "best_model": best_model,
                "model_version": model_version,
                "test_days": TEST_DAYS,
                "comparison": comparison,
                "improvement_over_naive_pct": improvement_pct,
                "cv_folds": cv_report,
                "error_by_store": _nest(by_store),
                "error_by_item": _nest(by_item),
                "error_by_store_item": _nest(by_store_item),
            }, f, indent=2)

        with open(out / "shap.json", "w") as f:
            json.dump(shap_report, f, indent=2)

        with open(out / "forecasts.json", "w") as f:
            json.dump(trimmed, f)

        # Save all 3 LGB models for runtime use.
        with open(out / "model_median.pkl", "wb") as f:
            pickle.dump(median_model, f)
        with open(out / "model_lower.pkl", "wb") as f:
            pickle.dump(lower_model, f)
        with open(out / "model_upper.pkl", "wb") as f:
            pickle.dump(upper_model, f)

        # Register best model in MLflow
        try:
            mlflow.lightgbm.log_model(median_model, "model", registered_model_name="stocksense_lgb")
        except Exception as e:
            print(f"[train] mlflow registration skipped: {e}")

        # Export experiments summary JSON
        exp_summary = {
            "run_id": run.info.run_id,
            "run_name": run.info.run_name,
            "start_time": run.info.start_time,
            "model_version": model_version,
            "params": {"horizon": HORIZON, "test_days": TEST_DAYS},
            "metrics": {f"{r['model']}_mape": r["mape"] for r in comparison},
            "best_model": best_model,
        }
        with open(out / "experiments.json", "w") as f:
            json.dump({"runs": [exp_summary]}, f, indent=2)

        # Model card
        with open(out / "model_card.json", "w") as f:
            json.dump({
                "name": "StockSense LightGBM Quantile Forecaster",
                "version": model_version,
                "task": "Daily demand forecasting (28-day horizon)",
                "architecture": "LightGBM gradient-boosted trees, 3 quantile models (0.1, 0.5, 0.9)",
                "training_data": f"{len(train_feats)} rows across {df['store'].nunique()} stores x {df['item'].nunique()} items",
                "features": FEATURE_COLS,
                "metrics": {"test_mape": lgb_m["mape"], "test_rmse": lgb_m["rmse"], "test_mae": lgb_m["mae"]},
                "intended_use": "Short-horizon retail store-item demand forecasting and inventory planning.",
                "limitations": [
                    "Assumes stationary promotional patterns.",
                    "Does not model stock-outs or price elasticity.",
                    "Prediction intervals assume quantile losses capture tail behaviour.",
                ],
                "ethical_considerations": [
                    "Over-forecasting leads to waste; under-forecasting creates stock-outs. "
                    "Review before fully automating orders.",
                ],
            }, f, indent=2)

        # Config file consumed by the API (list of (store, item) pairs available).
        pairs = sorted({(int(k.split("_")[0]), int(k.split("_")[1])) for k in trimmed.keys()})
        with open(out / "catalog.json", "w") as f:
            json.dump({
                "stores": sorted({p[0] for p in pairs}),
                "items": sorted({p[1] for p in pairs}),
                "pairs": [{"store": s, "item": i} for s, i in pairs],
                "model_version": model_version,
                "horizon": HORIZON,
            }, f, indent=2)

    print(f"[train] DONE. best={best_model} mape={lgb_m['mape']:.2f} (naive={naive_m['mape']:.2f})")
    print(f"[train] improvement over naive = {improvement_pct}%")
    return {"best_model": best_model, "lgb_mape": lgb_m["mape"], "naive_mape": naive_m["mape"]}


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/raw/train.csv")
    parser.add_argument("--out", default="backend/artifacts")
    parser.add_argument("--mlruns", default="mlruns")
    parser.add_argument("--sample", action="store_true", help="Smoke-test run on a small subset")
    args = parser.parse_args()
    run(args.data, args.out, args.mlruns, sample=args.sample)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
