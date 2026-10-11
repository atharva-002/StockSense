"""Quality-gate evaluator. Exits non-zero if the best model fails criteria."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", default="backend/artifacts/metrics.json")
    parser.add_argument("--max-mape", type=float, default=25.0,
                        help="Maximum acceptable MAPE for best model")
    args = parser.parse_args()

    p = Path(args.metrics)
    if not p.exists():
        print(f"[QUALITY-GATE] metrics file not found: {p}", file=sys.stderr)
        return 2

    with open(p) as f:
        data = json.load(f)

    best = data.get("best_model")
    comparison = data.get("comparison", [])
    if not best or not comparison:
        print("[QUALITY-GATE] malformed metrics", file=sys.stderr)
        return 2

    best_row = next((r for r in comparison if r["model"] == best), None)
    naive_row = next((r for r in comparison if "naive" in r["model"].lower()), None)
    if best_row is None:
        print("[QUALITY-GATE] best model row missing", file=sys.stderr)
        return 2

    best_mape = best_row["mape"]
    print(f"[QUALITY-GATE] best model = {best} with MAPE = {best_mape:.2f}%")

    if best_mape > args.max_mape:
        print(f"[QUALITY-GATE] FAIL: MAPE {best_mape:.2f}% > threshold {args.max_mape}%", file=sys.stderr)
        return 1
    if naive_row is not None and best_mape >= naive_row["mape"]:
        print(f"[QUALITY-GATE] FAIL: best model MAPE {best_mape:.2f}% is not better than naive {naive_row['mape']:.2f}%", file=sys.stderr)
        return 1

    print("[QUALITY-GATE] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
