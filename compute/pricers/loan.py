# compute/pricers/loan.py
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

def price_loan(position: dict, instrument: dict, market_snapshot: dict, measures: List[str], scenario_id: str) -> Dict[str, float]:
    snap = apply_scenario(market_snapshot, scenario_id)

    c_ois = _get_curve(snap, "USD-OIS")
    c_spread = _get_curve(snap, "LOAN-SPREAD")

    attrs = position.get("attributes", {})
    principal = float(attrs.get("current_principal", 0.0))
    coupon = float(attrs.get("coupon_rate", instrument.get("terms", {}).get("coupon_rate", 0.0)))

    cashflows = attrs.get("cashflows", [])
    if not cashflows:
        raise ValueError("MVP requires explicit cashflows in position.attributes.cashflows for loan")

    as_of = _parse_date(attrs.get("as_of_date"))
    last_pay = _parse_date(attrs.get("last_payment_date"))
    days = (as_of - last_pay).days
    accrual_frac = days / 360.0
    accrued_interest = principal * coupon * accrual_frac

    pv = 0.0
    for cf in cashflows:
        pay_date = _parse_date(cf["pay_date"])
        t = max((pay_date - as_of).days / 365.0, 0.0)
        df_ois = c_ois.df(t)
        spr = c_spread.zero(t)
        df = effective_df(df_ois, spr, t)
        amt = float(cf["interest"]) + float(cf["principal"])
        pv += amt * df

    out: Dict[str, float] = {}
    if "ACCRUED_INTEREST" in measures:
        out["ACCRUED_INTEREST"] = accrued_interest
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
            amt = float(cf["interest"]) + float(cf["principal"])
            pv_b += amt * df_b
        out["DV01"] = pv_b - pv
    return out
