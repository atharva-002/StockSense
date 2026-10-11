"""Lightweight drift monitoring: PSI + KS per feature, plus forecast-error drift.

No heavy libs; uses numpy + scipy.stats.ks_2samp.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10, eps: float = 1e-4) -> float:
    """Population Stability Index between two 1-D arrays."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Quantile bins from expected distribution.
    quantiles = np.unique(np.quantile(expected, np.linspace(0, 1, n_bins + 1)))
    if len(quantiles) < 3:
        quantiles = np.linspace(expected.min(), expected.max() + 1e-9, n_bins + 1)

    e_counts, _ = np.histogram(expected, bins=quantiles)
    a_counts, _ = np.histogram(actual, bins=quantiles)
    e_pct = e_counts / max(e_counts.sum(), 1)
    a_pct = a_counts / max(a_counts.sum(), 1)
    e_pct = np.where(e_pct == 0, eps, e_pct)
    a_pct = np.where(a_pct == 0, eps, a_pct)

    val = np.sum((a_pct - e_pct) * np.log(a_pct / e_pct))
    return float(val)


def psi_status(value: float) -> str:
    if value < 0.1:
        return "OK"
    if value < 0.25:
        return "WARNING"
    return "DRIFT"


def ks_test(expected: np.ndarray, actual: np.ndarray) -> tuple[float, float]:
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]
    if len(expected) < 2 or len(actual) < 2:
        return 0.0, 1.0
    res = stats.ks_2samp(expected, actual)
    return float(res.statistic), float(res.pvalue)


def ks_status(stat: float, pvalue: float) -> str:
    if pvalue > 0.05:
        return "OK"
    if stat < 0.2:
        return "WARNING"
    return "DRIFT"


def compute_drift_report(
    train_df: pd.DataFrame,
    new_df: pd.DataFrame,
    feature_cols: list[str],
    target: str = "sales",
) -> dict:
    features = []
    worst_status = "OK"
    rank = {"OK": 0, "WARNING": 1, "DRIFT": 2}

    for col in feature_cols + [target]:
        if col not in train_df.columns or col not in new_df.columns:
            continue
        e = train_df[col].dropna().values
        a = new_df[col].dropna().values
        p = psi(e, a)
        p_status = psi_status(p)
        k_stat, k_pval = ks_test(e, a)
        k_status = ks_status(k_stat, k_pval)

        row_status = p_status if rank[p_status] >= rank[k_status] else k_status
        if rank[row_status] > rank[worst_status]:
            worst_status = row_status

        features.append({
            "feature": col,
            "psi": round(p, 4),
            "psi_status": p_status,
            "ks_stat": round(k_stat, 4),
            "ks_pvalue": round(k_pval, 4),
            "ks_status": k_status,
            "status": row_status,
        })

    recommendation = {
        "OK": "No action needed. Model is healthy.",
        "WARNING": "Investigate drifting features. Consider retraining in next cycle.",
        "DRIFT": "Significant drift detected. Retraining recommended immediately.",
    }[worst_status]

    return {
        "overall_status": worst_status,
        "retrain_recommended": worst_status == "DRIFT",
        "recommendation": recommendation,
        "n_features_checked": len(features),
        "features": sorted(features, key=lambda f: -f["psi"]),
    }


def main() -> int:  # pragma: no cover - CLI
    import argparse

    from .features import FEATURE_COLS, build_feature_frame

    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default="data/raw/train.csv")
    parser.add_argument("--new", default="data/new/new_sales.csv")
    parser.add_argument("--out", default="backend/artifacts/drift_report.json")
    args = parser.parse_args()

    train = pd.read_csv(args.train, parse_dates=["date"])
    new = pd.read_csv(args.new, parse_dates=["date"])
    train_feats = build_feature_frame(train).dropna()
    new_feats = build_feature_frame(new).dropna()

    report = compute_drift_report(train_feats, new_feats, FEATURE_COLS)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Drift report -> {args.out} | overall: {report['overall_status']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
