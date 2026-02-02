# compute/pricers/fx_fwd.py
from __future__ import annotations
from typing import Dict, List
from compute.quantlib.curve import ZeroCurve
from compute.quantlib.scenarios import apply_scenario

def _get_curve(snapshot: dict, curve_id: str) -> ZeroCurve:
    for c in snapshot["curves"]:
        if c["curve_id"] == curve_id:
            return ZeroCurve.from_market_nodes(c["nodes"])
    raise KeyError(f"Curve not found: {curve_id}")

def _get_spot(snapshot: dict, pair: str) -> float:
    for q in snapshot["fx_spots"]:
        if q["pair"] == pair:
            return float(q["spot"])
    raise KeyError(f"FX spot not found: {pair}")

def price_fx_fwd(position: dict, instrument: dict, market_snapshot: dict, measures: List[str], scenario_id: str) -> Dict[str, float]:
    snap = apply_scenario(market_snapshot, scenario_id)

    fx_pair = instrument.get("underlyings", {}).get("fx_pair", "EURUSD")
    domestic = instrument.get("underlyings", {}).get("discount_curve_domestic", "USD-OIS")
    foreign = instrument.get("underlyings", {}).get("discount_curve_foreign", "EUR-OIS")

    c_dom = _get_curve(snap, domestic)
    c_for = _get_curve(snap, foreign)
    spot = _get_spot(snap, fx_pair)

    # MVP: approximate maturity as 1M
    t = 1/12

    fwd_rate = float(position.get("attributes", {}).get("forward_rate", 1.0))
    notional_base = float(position.get("attributes", {}).get("notional_base", 1_000_000.0))

    df_for = c_for.df(t)
    df_dom = c_dom.df(t)

    # PV in USD for long base forward:
    pv = notional_base * (spot * df_for - fwd_rate * df_dom)

    out: Dict[str, float] = {}
    if "PV" in measures:
        out["PV"] = pv
    if "FX_DELTA" in measures:
        out["FX_DELTA"] = notional_base * df_for
    if "DV01" in measures:
        bumped = apply_scenario(market_snapshot, "RATES_PARALLEL_1BP")
        c_dom_b = _get_curve(bumped, domestic)
        pv_b = notional_base * (spot * df_for - fwd_rate * c_dom_b.df(t))
        out["DV01"] = pv_b - pv
    return out
