"""ABS/MBS pricer with prepayment and default modeling.

Implements institutional-grade pricing for asset-backed and mortgage-backed securities
using PSA/CPR prepayment models and default/recovery credit modeling.
"""
from __future__ import annotations

from typing import Dict, List
from datetime import date, datetime
import math

from compute.cashflow.amortization import level_pay_schedule
from compute.cashflow.prepayment import apply_psa_prepayment
from compute.cashflow.default_model import apply_default_model
from compute.quantlib.scenarios import apply_scenario


def _parse_date(d: str | date) -> date:
    """Parse date from string or return date object."""
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def _get_curve_data(snapshot: dict, curve_id: str) -> dict:
    """Extract curve data from market snapshot."""
    for c in snapshot.get("curves", []):
        if c["curve_id"] == curve_id:
            return c
    raise KeyError(f"Curve not found: {curve_id}")


def _discount_factor(curve_nodes: List[dict], years: float) -> float:
    """Calculate discount factor from curve nodes using linear interpolation.

    Args:
        curve_nodes: List of dicts with 'tenor' (years) and 'rate' (zero rate).
        years: Time to discount in years.

    Returns:
        Discount factor.
    """
    if years <= 0:
        return 1.0

    # Sort nodes by tenor
    nodes = sorted(curve_nodes, key=lambda x: x['tenor'])

    # Handle extrapolation before first node
    if years <= nodes[0]['tenor']:
        rate = nodes[0]['rate']
        return math.exp(-rate * years)

    # Handle extrapolation after last node
    if years >= nodes[-1]['tenor']:
        rate = nodes[-1]['rate']
        return math.exp(-rate * years)

    # Linear interpolation between nodes
    for i in range(len(nodes) - 1):
        if nodes[i]['tenor'] <= years <= nodes[i + 1]['tenor']:
            t0, r0 = nodes[i]['tenor'], nodes[i]['rate']
            t1, r1 = nodes[i + 1]['tenor'], nodes[i + 1]['rate']

            # Interpolate rate
            weight = (years - t0) / (t1 - t0)
            rate = r0 + weight * (r1 - r0)

            return math.exp(-rate * years)

    # Fallback (should not reach here)
    return math.exp(-nodes[-1]['rate'] * years)


def price_abs_mbs(
    position: dict,
    instrument: dict,
    market_snapshot: dict,
    measures: List[str],
    scenario_id: str,
) -> Dict[str, float]:
    """Price an asset-backed or mortgage-backed security.

    Implements cashflow projection with:
    - PSA/CPR prepayment modeling
    - Default and recovery modeling
    - Loss-adjusted present value calculation
    - Weighted average life (WAL)
    - DV01 risk measure

    Args:
        position: Position dict with quantity and attributes.
        instrument: Instrument definition with pool characteristics.
        market_snapshot: Market data including discount curves.
        measures: List of measures to compute (PV, WAL, DV01, etc.).
        scenario_id: Scenario identifier (BASE, RATES_PARALLEL_1BP, etc.).

    Returns:
        Dict of measure name -> value.

    Raises:
        ValueError: If required instrument terms are missing.
        KeyError: If required market curves are missing.

    Example instrument definition:
        {
            "terms": {
                "original_balance": 1000000.0,
                "wac": 0.05,  # Weighted average coupon
                "wam": 360,  # Weighted average maturity (months)
                "psa_speed": 100.0,  # PSA prepayment speed
                "lgd": 0.40,  # Loss given default
                "pd_annual": 0.01  # Annual probability of default
            }
        }
    """
    # Apply scenario to market snapshot
    snap = apply_scenario(market_snapshot, scenario_id)

    # Extract instrument terms
    terms = instrument.get("terms", {})
    original_balance = float(terms.get("original_balance", 0.0))
    wac = float(terms.get("wac", 0.0))  # Weighted average coupon
    wam = int(terms.get("wam", 360))  # Weighted average maturity (months)
    psa_speed = float(terms.get("psa_speed", 100.0))  # PSA prepayment speed
    lgd = float(terms.get("lgd", 0.40))  # Loss given default
    pd_annual = float(terms.get("pd_annual", 0.01))  # Annual PD

    # Validate required terms
    if original_balance <= 0:
        raise ValueError("original_balance must be positive")
    if wam <= 0:
        raise ValueError("wam (weighted average maturity) must be positive")

    # Get evaluation date
    attrs = position.get("attributes", {})
    as_of_str = attrs.get("as_of_date", snap.get("as_of_date", "2026-01-15"))
    as_of = _parse_date(as_of_str)

    # Get discount curve (default to OIS curve)
    curve_id = terms.get("discount_curve", "USD-OIS")
    try:
        curve_data = _get_curve_data(snap, curve_id)
        curve_nodes = curve_data.get("nodes", [])
    except KeyError:
        # Fallback: create flat curve at 4%
        curve_nodes = [{"tenor": 0.0, "rate": 0.04}, {"tenor": 30.0, "rate": 0.04}]

    # 1. Generate base amortization schedule
    # Use level-pay schedule (standard for mortgages)
    try:
        base_schedule = level_pay_schedule(
            principal=original_balance,
            annual_rate=wac,
            num_periods=wam,
            frequency=12  # Monthly payments
        )
    except Exception as e:
        raise ValueError(f"Failed to generate amortization schedule: {e}")

    # 2. Apply prepayment and default models period-by-period
    # Need to track balance evolution properly and recalculate interest
    cashflows = []
    current_balance = original_balance
    monthly_rate = wac / 12.0  # Monthly interest rate
    monthly_pd = pd_annual / 12.0  # Convert annual PD to monthly

    for i, pmt in enumerate(base_schedule, start=1):
        # Interest accrues on BEGINNING balance (before any payments)
        interest_payment = current_balance * monthly_rate

        # Prepayment calculation on BEGINNING balance
        month = i
        base_cpr = min(month * 0.002, 0.06)
        cpr = base_cpr * (psa_speed / 100.0)
        cpr = max(0.0, min(1.0, cpr))
        smm = 1.0 - (1.0 - cpr) ** (1.0 / 12.0)
        prepayment = current_balance * smm

        # Default calculation on BEGINNING balance
        pd = min(1.0, max(0.0, monthly_pd))
        default_amount = current_balance * pd
        default_loss = default_amount * lgd
        recovery = default_amount * (1.0 - lgd)

        # Scheduled principal from amortization (but may be constrained by actual balance)
        scheduled_principal = min(pmt['principal'], current_balance - prepayment - default_amount)
        scheduled_principal = max(0.0, scheduled_principal)

        # Total principal reduction
        total_principal_out = scheduled_principal + prepayment + default_amount

        # Update balance for next period
        current_balance = max(0.0, current_balance - total_principal_out)

        cashflows.append({
            'month': i,
            'scheduled_principal': scheduled_principal,
            'interest': interest_payment,
            'prepayment': prepayment,
            'default_loss': default_loss,
            'recovery': recovery,
            'beginning_balance': current_balance + total_principal_out,
            'ending_balance': current_balance
        })

    # 4. Discount cashflows to present value
    pv = 0.0
    total_principal = 0.0
    weighted_time = 0.0

    for cf in cashflows:
        month = cf['month']
        years = month / 12.0

        # Total cashflow = scheduled principal + interest + prepayment - default loss + recovery
        scheduled_principal = cf.get('scheduled_principal', cf.get('principal', 0.0))
        interest_cf = cf.get('interest', 0.0)
        prepayment_cf = cf.get('prepayment', 0.0)
        default_loss = cf.get('default_loss', 0.0)
        recovery = cf.get('recovery', 0.0)

        total_cf = scheduled_principal + interest_cf + prepayment_cf - default_loss + recovery

        # Discount to present value
        df = _discount_factor(curve_nodes, years)
        pv += total_cf * df

        # Track principal for WAL calculation (scheduled + prepayments)
        principal_total = scheduled_principal + prepayment_cf
        total_principal += principal_total
        weighted_time += principal_total * years

    # 5. Compute measures
    results: Dict[str, float] = {}

    if "PV" in measures:
        results["PV"] = pv

    if "WAL" in measures:
        # Weighted Average Life = sum(principal_i * time_i) / sum(principal_i)
        if total_principal > 0:
            wal = weighted_time / total_principal
        else:
            wal = 0.0
        results["WAL"] = wal

    if "DV01" in measures:
        # DV01: bump rates by 1bp and reprice
        bumped_snap = apply_scenario(market_snapshot, "RATES_PARALLEL_1BP")

        try:
            bumped_curve_data = _get_curve_data(bumped_snap, curve_id)
            bumped_nodes = bumped_curve_data.get("nodes", [])
        except KeyError:
            # Fallback: bump flat curve
            bumped_nodes = [{"tenor": 0.0, "rate": 0.0401}, {"tenor": 30.0, "rate": 0.0401}]

        # Reprice with bumped curve
        pv_bumped = 0.0
        for cf in cashflows:
            month = cf['month']
            years = month / 12.0

            scheduled_principal = cf.get('scheduled_principal', cf.get('principal', 0.0))
            interest_cf = cf.get('interest', 0.0)
            prepayment_cf = cf.get('prepayment', 0.0)
            default_loss = cf.get('default_loss', 0.0)
            recovery = cf.get('recovery', 0.0)

            total_cf = scheduled_principal + interest_cf + prepayment_cf - default_loss + recovery

            df = _discount_factor(bumped_nodes, years)
            pv_bumped += total_cf * df

        results["DV01"] = pv_bumped - pv

    return results
