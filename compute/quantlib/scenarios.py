# compute/quantlib/scenarios.py
from __future__ import annotations
import copy

def apply_scenario(snapshot: dict, scenario_id: str) -> dict:
    s = copy.deepcopy(snapshot)
    if scenario_id == "BASE":
        return s

    if scenario_id == "RATES_PARALLEL_1BP":
        bump = 0.0001
        for c in s.get("curves", []):
            if c.get("curve_id") in ("USD-OIS", "EUR-OIS"):
                for n in c.get("nodes", []):
                    n["zero_rate"] = float(n["zero_rate"]) + bump
        return s

    if scenario_id == "SPREAD_25BP":
        bump = 0.0025
        for c in s.get("curves", []):
            if c.get("curve_id") in ("LOAN-SPREAD", "FI-SPREAD"):
                for n in c.get("nodes", []):
                    n["zero_rate"] = float(n["zero_rate"]) + bump
        return s

    if scenario_id == "FX_SPOT_1PCT":
        for q in s.get("fx_spots", []):
            q["spot"] = float(q["spot"]) * 1.01
        return s

    raise ValueError(f"Unsupported scenario_id: {scenario_id}")
