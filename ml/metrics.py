"""Forecasting metric helpers."""
from __future__ import annotations

import numpy as np


def _as_arr(a):
    return np.asarray(a, dtype=float)


def mae(y_true, y_pred) -> float:
    y, p = _as_arr(y_true), _as_arr(y_pred)
    return float(np.mean(np.abs(y - p)))


def rmse(y_true, y_pred) -> float:
    y, p = _as_arr(y_true), _as_arr(y_pred)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def mape(y_true, y_pred) -> float:
    """Mean absolute percentage error. Skips true-zero rows to avoid division by zero."""
    y, p = _as_arr(y_true), _as_arr(y_pred)
    mask = y != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y[mask] - p[mask]) / y[mask])) * 100.0)


def smape(y_true, y_pred) -> float:
    """Symmetric MAPE."""
    y, p = _as_arr(y_true), _as_arr(y_pred)
    denom = (np.abs(y) + np.abs(p)) / 2.0
    mask = denom != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs(y[mask] - p[mask]) / denom[mask]) * 100.0)


def all_metrics(y_true, y_pred) -> dict:
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "smape": smape(y_true, y_pred),
    }
