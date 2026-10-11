import numpy as np

from ml.drift import ks_test, psi, psi_status


def test_psi_identical_near_zero():
    rng = np.random.default_rng(0)
    base = rng.normal(0, 1, 5000)
    actual = rng.normal(0, 1, 5000)
    val = psi(base, actual)
    assert val < 0.1
    assert psi_status(val) == "OK"


def test_psi_large_shift_detects_drift():
    rng = np.random.default_rng(0)
    base = rng.normal(0, 1, 5000)
    actual = rng.normal(3, 1, 5000)  # mean shift of 3 sigma
    val = psi(base, actual)
    assert val > 0.25
    assert psi_status(val) == "DRIFT"


def test_ks_detects_shift():
    rng = np.random.default_rng(1)
    stat, pval = ks_test(rng.normal(0, 1, 2000), rng.normal(1.5, 1, 2000))
    assert pval < 0.05
    assert stat > 0.2
