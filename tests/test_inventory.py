import math

from ml.inventory import compute_inventory


def test_safety_stock_grows_with_service_level():
    f_mean = [10] * 28
    f_up = [14] * 28
    f_lo = [6] * 28
    low = compute_inventory(f_mean, f_up, f_lo, lead_time_days=7, service_level=0.80)
    high = compute_inventory(f_mean, f_up, f_lo, lead_time_days=7, service_level=0.99)
    assert high.safety_stock > low.safety_stock


def test_reorder_point_includes_lead_time_demand():
    f_mean = [10] * 28
    inv = compute_inventory(f_mean, lead_time_days=5, service_level=0.95)
    # ROP must be >= mean daily demand * lead_time
    assert inv.reorder_point >= inv.mean_daily_demand * 5


def test_order_quantity_nonnegative():
    f_mean = [10] * 28
    inv = compute_inventory(f_mean, lead_time_days=5, on_hand=10_000)
    assert inv.order_quantity >= 0


def test_longer_lead_time_increases_safety():
    f_mean = [10] * 28
    short = compute_inventory(f_mean, lead_time_days=2, service_level=0.95)
    long_ = compute_inventory(f_mean, lead_time_days=20, service_level=0.95)
    # sqrt(L) scaling
    assert long_.safety_stock > short.safety_stock
    assert math.isclose(
        long_.safety_stock / short.safety_stock,
        math.sqrt(20) / math.sqrt(2),
        rel_tol=0.05,
    )
