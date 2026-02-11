"""Structured product pricer (CLO, CDO, ABS).

Implements tranche valuation using waterfall logic to allocate collateral cashflows.
Supports senior, mezzanine, and equity tranches with priority-of-payments structures.
"""
from __future__ import annotations

from typing import Dict, List
import copy
import QuantLib as ql
from compute.cashflow.waterfall import apply_waterfall
from compute.quantlib.curve_builder import build_discount_curve


def price_structured(
    position: dict,
    instrument: dict,
    market_snapshot: dict,
    measures: List[str],
    scenario_id: str,
) -> Dict[str, float]:
    """Price a structured product tranche (CLO, CDO, etc.).

    Uses waterfall logic to allocate collateral cashflows across tranches.
    Discounts allocated cashflows to compute tranche PV.

    Args:
        position: Position dict with tranche_id, notional
        instrument: Instrument dict with tranches, collateral_cashflows
        market_snapshot: Market data with curves, evaluation date
        measures: List of measures to compute (PV, YIELD, COVERAGE_RATIO)
        scenario_id: Scenario identifier

    Returns:
        Dict mapping measure names to computed values.
    """
    # Apply scenario to market data
    snap = _apply_scenario(market_snapshot, scenario_id)

    # Get evaluation date
    eval_date_str = snap.get("snapshot_date", "2026-02-15")
    year, month, day = eval_date_str.split("-")
    eval_date = ql.Date(int(day), int(month), int(year))
    ql.Settings.instance().evaluationDate = eval_date

    # Get tranche being priced
    tranche_id = position.get("tranche_id")
    if not tranche_id:
        raise ValueError("Position must specify tranche_id for structured products")

    # Get tranche structure from instrument
    tranches = instrument.get("tranches", [])
    if not tranches:
        raise ValueError("Instrument must specify tranches structure")

    # Get collateral cashflows from instrument
    collateral_cashflows = instrument.get("collateral_cashflows", [])
    if not collateral_cashflows:
        # Fallback: Use simplified approach if collateral cashflows not available
        # Prorate collateral PV by tranche subordination
        return _price_structured_simplified(position, instrument, snap, measures, eval_date)

    # Apply waterfall to allocate collateral cashflows to tranches
    tranche_cashflows = apply_waterfall(collateral_cashflows, tranches)

    # Get allocated cashflows for the specific tranche being priced
    if tranche_id not in tranche_cashflows:
        raise ValueError(f"Tranche {tranche_id} not found in waterfall results")

    allocated_cashflows = tranche_cashflows[tranche_id]

    # Build discount curve
    discount_curve = _build_curve_from_snapshot(snap, "USD-OIS", eval_date)

    # Compute measures
    results: Dict[str, float] = {}

    if "PV" in measures:
        # Discount allocated cashflows
        pv = 0.0
        for cf in allocated_cashflows:
            period = cf.get("period", 1)
            interest = cf.get("interest", 0.0)
            principal = cf.get("principal", 0.0)
            excess = cf.get("excess", 0.0)
            total_cf = interest + principal + excess

            # Discount factor (simplified: assume annual periods)
            t = period  # years from eval_date
            df = discount_curve.discount(eval_date + ql.Period(int(t * 12), ql.Months))
            pv += total_cf * df

        results["PV"] = pv

    if "YIELD" in measures:
        # Compute IRR from tranche cashflows
        # Simplified: use approximate yield calculation
        total_cf = sum(
            cf.get("interest", 0.0) + cf.get("principal", 0.0) + cf.get("excess", 0.0)
            for cf in allocated_cashflows
        )
        tranche_notional = float(position.get("attributes", {}).get("notional", 1_000_000.0))
        avg_maturity = len(allocated_cashflows)  # years

        if avg_maturity > 0 and tranche_notional > 0:
            # Approximate yield: (total_cf / notional - 1) / maturity
            approx_yield = (total_cf / tranche_notional - 1.0) / avg_maturity
            results["YIELD"] = approx_yield
        else:
            results["YIELD"] = 0.0

    if "COVERAGE_RATIO" in measures:
        # Coverage ratio: collateral value / tranche notional
        total_collateral = sum(
            cf.get("interest", 0.0) + cf.get("principal", 0.0)
            for cf in collateral_cashflows
        )
        tranche_notional = float(position.get("attributes", {}).get("notional", 1_000_000.0))

        if tranche_notional > 0:
            results["COVERAGE_RATIO"] = total_collateral / tranche_notional
        else:
            results["COVERAGE_RATIO"] = 0.0

    return results


def _price_structured_simplified(
    position: dict,
    instrument: dict,
    snapshot: dict,
    measures: List[str],
    eval_date: ql.Date,
) -> Dict[str, float]:
    """Simplified structured product pricing when collateral cashflows not available.

    Prorates collateral PV by tranche subordination level.
    This is a fallback approach and may not accurately reflect waterfall dynamics.

    Args:
        position: Position dict
        instrument: Instrument dict
        snapshot: Market snapshot
        measures: Measures to compute
        eval_date: Evaluation date

    Returns:
        Dict of computed measures.
    """
    tranche_id = position.get("tranche_id")
    tranches = instrument.get("tranches", [])

    # Find tranche info
    tranche_info = None
    for t in tranches:
        if t.get("tranche_id") == tranche_id:
            tranche_info = t
            break

    if not tranche_info:
        raise ValueError(f"Tranche {tranche_id} not found in tranches")

    # Get collateral PV (simplified: use notional * recovery assumption)
    collateral_pv = float(instrument.get("collateral_pv", 100_000_000.0))
    tranche_notional = float(tranche_info.get("notional", 1_000_000.0))
    tranche_priority = int(tranche_info.get("priority", 1))

    # Prorate PV by subordination (higher priority = more value)
    # Simplified: assume linear subordination
    total_tranches = len(tranches)
    subordination_factor = (total_tranches - tranche_priority + 1) / total_tranches

    results: Dict[str, float] = {}

    if "PV" in measures:
        # Simplified PV allocation
        results["PV"] = (tranche_notional / collateral_pv) * collateral_pv * subordination_factor

    if "YIELD" in measures:
        # Simplified yield estimate
        coupon = float(tranche_info.get("coupon", 0.05))
        results["YIELD"] = coupon * subordination_factor

    if "COVERAGE_RATIO" in measures:
        results["COVERAGE_RATIO"] = collateral_pv / tranche_notional if tranche_notional > 0 else 0.0

    return results


def _build_curve_from_snapshot(
    snapshot: dict,
    curve_id: str,
    eval_date: ql.Date,
) -> ql.YieldTermStructure:
    """Build QuantLib curve from market snapshot data.

    Args:
        snapshot: Market snapshot with curves list
        curve_id: Curve identifier (e.g., 'USD-OIS')
        eval_date: Evaluation date

    Returns:
        QuantLib YieldTermStructure
    """
    # Find curve in snapshot
    curve_data = None
    for curve in snapshot.get("curves", []):
        if curve.get("curve_id") == curve_id:
            curve_data = curve
            break

    if not curve_data:
        raise ValueError(f"Curve {curve_id} not found in market snapshot")

    # Build market data structure for curve_builder
    instruments = []
    for node in curve_data.get("nodes", []):
        instruments.append({
            "type": "DEPOSIT" if node.get("tenor", "3M").endswith("M") and "Y" not in node.get("tenor", "") else "SWAP",
            "rate": node.get("rate", 0.04),
            "tenor": node.get("tenor", "1Y"),
            "fixing_days": 2,
        })

    market_data = {
        "calc_date": eval_date,
        "instruments": instruments,
    }

    return build_discount_curve(market_data, curve_id)


def _apply_scenario(market_snapshot: dict, scenario_id: str) -> dict:
    """Apply scenario to market snapshot.

    Args:
        market_snapshot: Market snapshot dict
        scenario_id: Scenario identifier (BASE, RATES_UP, RATES_DOWN, etc.)

    Returns:
        Modified market snapshot with scenario applied
    """
    # Deep copy curves to avoid modifying original
    snapshot = {
        "snapshot_date": market_snapshot.get("snapshot_date"),
        "curves": copy.deepcopy(market_snapshot.get("curves", [])),
        "scenarios": market_snapshot.get("scenarios", {})
    }

    if scenario_id == "BASE":
        return snapshot

    # Check for custom scenarios in market data
    scenarios = snapshot.get("scenarios", {})
    if scenario_id in scenarios:
        scenario = scenarios[scenario_id]

        if scenario["type"] == "PARALLEL_SHIFT":
            shift = float(scenario["shift"])
            affected_curves = scenario.get("curves", [])

            for curve in snapshot.get("curves", []):
                if curve["curve_id"] in affected_curves:
                    # Apply parallel shift to all nodes
                    for node in curve.get("nodes", []):
                        node["rate"] = float(node["rate"]) + shift

        return snapshot

    raise ValueError(f"Unsupported scenario_id: {scenario_id}")
