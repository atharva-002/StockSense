"""Feature engineering for StockSense demand forecasting.

All lag/rolling features use ONLY past data (no leakage).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LAGS = [7, 14, 28, 364]
ROLLING_WINDOWS = [7, 14, 28]

# Observed US public holidays within 2013-2018 (date-only, static for reproducibility).
US_HOLIDAYS = {
    "2013-01-01", "2013-07-04", "2013-11-28", "2013-12-25",
    "2014-01-01", "2014-07-04", "2014-11-27", "2014-12-25",
    "2015-01-01", "2015-07-04", "2015-11-26", "2015-12-25",
    "2016-01-01", "2016-07-04", "2016-11-24", "2016-12-25",
    "2017-01-01", "2017-07-04", "2017-11-23", "2017-12-25",
    "2018-01-01", "2018-07-04", "2018-11-22", "2018-12-25",
}


def add_calendar_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Add deterministic calendar features (no leakage, pure functions of the date)."""
    out = df.copy()
    d = pd.to_datetime(out[date_col])
    out["dayofweek"] = d.dt.dayofweek.astype(np.int16)
    out["day"] = d.dt.day.astype(np.int16)
    out["month"] = d.dt.month.astype(np.int16)
    out["year"] = d.dt.year.astype(np.int16)
    out["weekofyear"] = d.dt.isocalendar().week.astype(np.int16)
    out["quarter"] = d.dt.quarter.astype(np.int16)
    out["is_weekend"] = (out["dayofweek"] >= 5).astype(np.int8)
    iso = d.dt.strftime("%Y-%m-%d")
    out["is_holiday"] = iso.isin(US_HOLIDAYS).astype(np.int8)
    return out


def add_lag_features(
    df: pd.DataFrame,
    target: str = "sales",
    group_cols: tuple[str, ...] = ("store", "item"),
    lags: list[int] | None = None,
    rolling_windows: list[int] | None = None,
) -> pd.DataFrame:
    """Add lag and rolling features computed strictly from PAST values per (store, item).

    Rolling features are shifted by 1 so the current row is excluded (no leakage).
    """
    lags = list(lags) if lags is not None else LAGS
    rolling_windows = list(rolling_windows) if rolling_windows is not None else ROLLING_WINDOWS

    df = df.sort_values(list(group_cols) + ["date"]).reset_index(drop=True)
    grp = df.groupby(list(group_cols), sort=False)[target]

    for lag in lags:
        df[f"lag_{lag}"] = grp.shift(lag).astype(np.float32)

    for w in rolling_windows:
        shifted = grp.shift(1)
        df[f"rmean_{w}"] = shifted.rolling(w, min_periods=1).mean().reset_index(level=0, drop=True).astype(np.float32)
        df[f"rstd_{w}"] = shifted.rolling(w, min_periods=1).std().reset_index(level=0, drop=True).astype(np.float32)

    return df


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience: run calendar then lag features together."""
    out = add_calendar_features(df)
    out = add_lag_features(out)
    out["store"] = out["store"].astype(np.int16)
    out["item"] = out["item"].astype(np.int16)
    return out


FEATURE_COLS = (
    ["store", "item", "dayofweek", "day", "month", "year",
     "weekofyear", "quarter", "is_weekend", "is_holiday"]
    + [f"lag_{k}" for k in LAGS]
    + [f"rmean_{w}" for w in ROLLING_WINDOWS]
    + [f"rstd_{w}" for w in ROLLING_WINDOWS]
)
