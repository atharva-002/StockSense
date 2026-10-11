"""Inventory optimisation from forecasts.

Formulas:
  safety_stock      = z * sigma_LT              where sigma_LT = sigma_daily * sqrt(L)
  reorder_point     = mu_daily * L + safety_stock
  order_quantity    = EOQ (fallback: mu_daily * review_period + safety_stock - on_hand)
  stockout_risk     = Prob(demand_during_LT > on_hand) estimated from forecast quantiles

z-values for common service levels (two-sided -> use one-tailed inv-normal):
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# One-tailed z-scores for selected service levels.
Z_TABLE = {
    0.80: 0.8416,
    0.85: 1.0364,
    0.90: 1.2816,
    0.95: 1.6449,
    0.975: 1.9600,
    0.99: 2.3263,
}


def _z_for(service_level: float) -> float:
    # Clamp and look up nearest known SL; fall back to 1.645 for 95%.
    service_level = max(0.5, min(service_level, 0.995))
    best = min(Z_TABLE.keys(), key=lambda k: abs(k - service_level))
    return Z_TABLE[best]


@dataclass
class InventoryResult:
    mean_daily_demand: float
    sigma_daily_demand: float
    lead_time_days: int
    service_level: float
    z: float
    safety_stock: float
    reorder_point: float
    order_quantity: float
    stockout_risk: str  # "low" | "medium" | "high"
    expected_lt_demand: float
    expected_lt_upper: float

    def to_dict(self) -> dict:
        return {
            "mean_daily_demand": round(self.mean_daily_demand, 3),
            "sigma_daily_demand": round(self.sigma_daily_demand, 3),
            "lead_time_days": self.lead_time_days,
            "service_level": self.service_level,
            "z": self.z,
            "safety_stock": round(self.safety_stock, 2),
            "reorder_point": round(self.reorder_point, 2),
            "order_quantity": round(self.order_quantity, 2),
            "stockout_risk": self.stockout_risk,
            "expected_lt_demand": round(self.expected_lt_demand, 2),
            "expected_lt_upper": round(self.expected_lt_upper, 2),
        }


def compute_inventory(
    forecast_mean: list[float],
    forecast_upper: list[float] | None = None,
    forecast_lower: list[float] | None = None,
    lead_time_days: int = 7,
    service_level: float = 0.95,
    review_period_days: int = 14,
    on_hand: float = 0.0,
) -> InventoryResult:
    """Compute inventory decisions from a horizon-length forecast.

    Uses mean of forecast as mu_daily, std of forecast as sigma_daily proxy.
    """
    if not forecast_mean:
        raise ValueError("forecast_mean is empty")
    L = max(1, int(lead_time_days))
    sl = float(service_level)
    z = _z_for(sl)

    mu = sum(forecast_mean) / len(forecast_mean)

    if forecast_upper is not None and forecast_lower is not None and len(forecast_upper) == len(forecast_mean):
        # Approx sigma from quantile band (~ (upper - lower) / (2 * 1.645)) for a ~90% interval.
        bands = [(u - lo) / (2 * 1.6449) for u, lo in zip(forecast_upper, forecast_lower)]
        sigma = sum(bands) / len(bands)
    else:
        var = sum((x - mu) ** 2 for x in forecast_mean) / max(1, len(forecast_mean) - 1)
        sigma = math.sqrt(var)
    sigma = max(sigma, 1e-3)

    sigma_lt = sigma * math.sqrt(L)
    safety = z * sigma_lt
    rop = mu * L + safety
    # Simple (R, S) policy: order up to covering review period + lead time with safety stock.
    order_q = max(0.0, mu * (review_period_days + L) + safety - on_hand)

    # Stock-out risk tiering from headroom (on_hand vs reorder_point).
    headroom = (on_hand - rop) if on_hand else -rop
    if on_hand == 0:
        risk = "high" if rop > 10 * mu else "medium"
    elif on_hand < rop:
        risk = "high"
    elif headroom < safety:
        risk = "medium"
    else:
        risk = "low"

    lt_mean = mu * L
    lt_upper = (sum(forecast_upper[:L]) if forecast_upper else (mu + z * sigma) * L)

    return InventoryResult(
        mean_daily_demand=mu,
        sigma_daily_demand=sigma,
        lead_time_days=L,
        service_level=sl,
        z=z,
        safety_stock=safety,
        reorder_point=rop,
        order_quantity=order_q,
        stockout_risk=risk,
        expected_lt_demand=lt_mean,
        expected_lt_upper=lt_upper,
    )
