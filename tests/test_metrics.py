import numpy as np
import pytest

from ml.metrics import mae, mape, rmse, smape


def test_mae_rmse_mape_basic():
    y = np.array([10, 20, 30, 40])
    p = np.array([12, 18, 33, 39])
    assert mae(y, p) == pytest.approx(2.0)
    assert rmse(y, p) == pytest.approx(np.sqrt((4 + 4 + 9 + 1) / 4))
    # MAPE = mean(|y-p|/|y|) * 100
    assert mape(y, p) == pytest.approx(
        np.mean([2 / 10, 2 / 20, 3 / 30, 1 / 40]) * 100
    )


def test_mape_skips_zero():
    y = np.array([0, 10, 20])
    p = np.array([1, 9, 22])
    # Only the two non-zero y's contribute: |1|/10, |2|/20 = (0.1 + 0.1)/2 = 0.1 -> 10%
    assert mape(y, p) == pytest.approx(10.0)


def test_smape_symmetry():
    assert smape([10], [12]) == smape([12], [10])
