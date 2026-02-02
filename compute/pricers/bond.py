# compute/pricers/bond.py
from __future__ import annotations
from typing import Dict, List
from datetime import date, datetime
from compute.quantlib.curve import ZeroCurve, effective_df
from compute.quantlib.scenarios import apply_scenario

def _get_curve(snapshot: dict, curve_id: str) -> ZeroCurve:
    for c in snapshot["curves"]:
        if c["curve_id"] == curve_id:
            return ZeroCurve.from_market_nodes(c["nodes"])
    raise KeyError(f"Curve not found: {curve_id}")

def _parse_date(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()

def price_bond(position: dict, instrument: dict, market_snapshot: dict, measures: List[str], scenario_id: str) -> Dict[str, float]:
    snap = apply_scenario(market_snapshot, scenario_id)

    c_ois = _get_curve(snap, "USD-OIS")
    c_spread = _get_curve(snap, "FI-SPREAD")

    attrs = position.get("attributes", {})
    as_of = _parse_date(attrs.get("as_of_date"))

    cashflows = attrs.get("cashflows", [])
    if not cashflows:
        raise ValueError("MVP requires explicit cashflows in position.attributes.cashflows for bond")

    accrued = float(attrs.get("accrued_interest", 0.0))

    pv = 0.0
    for cf in cashflows:
        pay_date = _parse_date(cf["pay_date"])
        t = max((pay_date - as_of).days / 365.0, 0.0)
        df_ois = c_ois.df(t)
        spr = c_spread.zero(t)
        df = effective_df(df_ois, spr, t)
        pv += float(cf["amount"]) * df

    out: Dict[str, float] = {}
    if "ACCRUED_INTEREST" in measures:
        out["ACCRUED_INTEREST"] = accrued
    if "PV" in measures:
        out["PV"] = pv
    if "DV01" in measures:
        bumped = apply_scenario(market_snapshot, "RATES_PARALLEL_1BP")
        c_ois_b = _get_curve(bumped, "USD-OIS")
        pv_b = 0.0
        for cf in cashflows:
            pay_date = _parse_date(cf["pay_date"])
            t = max((pay_date - as_of).days / 365.0, 0.0)
            df_ois_b = c_ois_b.df(t)
            spr = c_spread.zero(t)
            df_b = effective_df(df_ois_b, spr, t)
            pv_b += float(cf["amount"]) * df_b
        out["DV01"] = pv_b - pv
    return out
