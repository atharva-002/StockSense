"""Guarantee no data leakage in lag features: lag_K at date t equals sales at t-K."""
import numpy as np
import pandas as pd

from ml.features import add_calendar_features, add_lag_features


def _toy():
    dates = pd.date_range("2020-01-01", periods=400, freq="D")
    df = pd.DataFrame({
        "date": list(dates) * 2,
        "store": [1] * 400 + [2] * 400,
        "item": [1] * 800,
        "sales": list(range(400)) + list(range(1000, 1400)),
    })
    return df


def test_calendar_features_shape():
    df = _toy()
    out = add_calendar_features(df)
    for col in ["dayofweek", "day", "month", "year", "weekofyear", "quarter", "is_weekend", "is_holiday"]:
        assert col in out.columns
    assert out["dayofweek"].between(0, 6).all()
    assert out["month"].between(1, 12).all()


def test_lag_features_no_leakage():
    df = _toy()
    out = add_lag_features(df, lags=[7, 14], rolling_windows=[7])
    # pick a store-item series
    g = out[(out["store"] == 1) & (out["item"] == 1)].sort_values("date").reset_index(drop=True)
    # For index 20 (date is 21st), lag_7 should equal sales at index 13.
    assert g.loc[20, "lag_7"] == g.loc[13, "sales"]
    assert g.loc[20, "lag_14"] == g.loc[6, "sales"]
    # Rolling mean at idx 20 window=7: uses PAST 7 values (idx 13..19).
    expected = np.mean(g.loc[13:19, "sales"].values)
    assert np.isclose(g.loc[20, "rmean_7"], expected, atol=1e-5)


def test_lag_features_respect_groups():
    df = _toy()
    out = add_lag_features(df, lags=[1])
    # First row of each group must have NaN lag_1 (no past value).
    first_rows = out.sort_values(["store", "item", "date"]).groupby(["store", "item"]).head(1)
    assert first_rows["lag_1"].isna().all()
