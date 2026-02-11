"""Derivatives pricer for interest rate swaps.

Implements vanilla interest rate swap pricing using QuantLib's multi-curve framework.
Focus on hedging instruments for fixed income portfolios (pay-fixed/receive-floating).

Future extensions: swaptions, caps/floors, credit default swaps.
"""
from __future__ import annotations

from typing import Dict, List
import QuantLib as ql
from compute.quantlib.curve_builder import build_discount_curve, build_forward_curve


def price_derivatives(
    position: dict,
    instrument: dict,
    market_snapshot: dict,
    measures: List[str],
    scenario_id: str,
) -> Dict[str, float]:
    """Price a derivative instrument (vanilla interest rate swap).

    Supports:
    - PAY_FIXED swaps (pay fixed rate, receive floating)
    - RECEIVE_FIXED swaps (receive fixed rate, pay floating)

    Multi-curve framework:
    - OIS curve for discounting
    - SOFR curve for forward rate projection

    Args:
        position: Position dict with notional, quantity
        instrument: Instrument dict with swap_type, fixed_rate, maturity, etc.
        market_snapshot: Market data with curves, evaluation date
        measures: List of measures to compute (PV, DV01, FIXED_LEG_PV, FLOAT_LEG_PV)
        scenario_id: Scenario identifier (BASE, RATES_PARALLEL_1BP, etc.)

    Returns:
        Dict mapping measure names to computed values.
    """
    # Apply scenario to market data
    # For MVP, scenario application is simplified (will be enhanced in scenario engine)
    snap = market_snapshot.copy()

    # Extract swap parameters from instrument
    swap_type = instrument.get("swap_type", "PAY_FIXED")  # PAY_FIXED or RECEIVE_FIXED
    fixed_rate = float(instrument.get("fixed_rate", 0.04))  # e.g., 4%
    maturity_years = float(instrument.get("maturity_years", 5))
    notional = float(position.get("attributes", {}).get("notional", 1_000_000.0))

    # Get evaluation date from market snapshot
    eval_date_str = snap.get("snapshot_date", "2026-02-15")
    year, month, day = eval_date_str.split("-")
    eval_date = ql.Date(int(day), int(month), int(year))
    ql.Settings.instance().evaluationDate = eval_date

    # Build OIS discount curve and SOFR forward curve (multi-curve framework)
    ois_curve = _build_curve_from_snapshot(snap, "USD-OIS", eval_date)
    sofr_curve = _build_curve_from_snapshot(snap, "USD-SOFR", eval_date)

    # Create QuantLib VanillaSwap
    swap = _create_vanilla_swap(
        swap_type=swap_type,
        notional=notional,
        fixed_rate=fixed_rate,
        maturity_years=maturity_years,
        eval_date=eval_date,
        ois_curve=ois_curve,
        sofr_curve=sofr_curve,
    )

    # Compute requested measures
    results: Dict[str, float] = {}

    if "PV" in measures:
        results["PV"] = swap.NPV()

    if "FIXED_LEG_PV" in measures:
        results["FIXED_LEG_PV"] = swap.fixedLegNPV()

    if "FLOAT_LEG_PV" in measures:
        results["FLOAT_LEG_PV"] = swap.floatingLegNPV()

    if "DV01" in measures:
        # Compute DV01 via bump-reprice
        # Bump OIS curve by +1bp and reprice
        bumped_ois = _bump_curve(ois_curve, 0.0001, eval_date)
        bumped_swap = _create_vanilla_swap(
            swap_type=swap_type,
            notional=notional,
            fixed_rate=fixed_rate,
            maturity_years=maturity_years,
            eval_date=eval_date,
            ois_curve=bumped_ois,
            sofr_curve=sofr_curve,
        )
        pv_bumped = bumped_swap.NPV()
        pv_base = swap.NPV()
        results["DV01"] = pv_bumped - pv_base

    return results


def _build_curve_from_snapshot(
    snapshot: dict,
    curve_id: str,
    eval_date: ql.Date,
) -> ql.YieldTermStructure:
    """Build QuantLib curve from market snapshot data.

    Args:
        snapshot: Market snapshot with curves list
        curve_id: Curve identifier (e.g., 'USD-OIS', 'USD-SOFR')
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
    # Convert snapshot nodes to QuantLib instruments
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


def _create_vanilla_swap(
    swap_type: str,
    notional: float,
    fixed_rate: float,
    maturity_years: float,
    eval_date: ql.Date,
    ois_curve: ql.YieldTermStructure,
    sofr_curve: ql.YieldTermStructure,
) -> ql.VanillaSwap:
    """Create QuantLib VanillaSwap object.

    Args:
        swap_type: 'PAY_FIXED' or 'RECEIVE_FIXED'
        notional: Swap notional amount
        fixed_rate: Fixed leg rate
        maturity_years: Swap maturity in years
        eval_date: Evaluation date
        ois_curve: OIS discount curve
        sofr_curve: SOFR forward curve

    Returns:
        QuantLib VanillaSwap object with pricing engine attached.
    """
    # Determine swap type
    if swap_type == "PAY_FIXED":
        swap_type_ql = ql.VanillaSwap.Payer
    elif swap_type == "RECEIVE_FIXED":
        swap_type_ql = ql.VanillaSwap.Receiver
    else:
        raise ValueError(f"Unknown swap type: {swap_type}")

    # Set up swap parameters
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    settlement_days = 2
    maturity = eval_date + ql.Period(int(maturity_years * 12), ql.Months)

    # Fixed leg schedule (semiannual)
    fixed_schedule = ql.Schedule(
        eval_date,
        maturity,
        ql.Period(ql.Semiannual),
        calendar,
        ql.ModifiedFollowing,
        ql.ModifiedFollowing,
        ql.DateGeneration.Forward,
        False,  # end of month
    )

    # Floating leg schedule (quarterly, SOFR 3M)
    floating_schedule = ql.Schedule(
        eval_date,
        maturity,
        ql.Period(ql.Quarterly),
        calendar,
        ql.ModifiedFollowing,
        ql.ModifiedFollowing,
        ql.DateGeneration.Forward,
        False,
    )

    # Create SOFR index (3M)
    # Link the forward curve to the index for projection
    sofr_index_handle = ql.YieldTermStructureHandle(sofr_curve)
    sofr_index = ql.USDLibor(ql.Period("3M"), sofr_index_handle)
    # Note: In production, would create proper SOFR index. Using USDLibor as proxy for MVP.

    # Add historical fixing for the first coupon (if needed)
    # QuantLib requires a fixing for the first floating coupon's fixing date
    # For swaps starting on eval_date, the fixing date is typically 2 business days prior
    fixing_date = eval_date - ql.Period(2, ql.Days)
    try:
        # Try to get the fixing; if it doesn't exist, add it
        _ = sofr_index.fixing(fixing_date)
    except RuntimeError:
        # Add a fixing using the current forward rate
        # This is the market-implied rate for that date
        fixing_rate = sofr_curve.forwardRate(
            eval_date,
            eval_date + ql.Period(3, ql.Months),
            ql.Actual360(),
            ql.Simple
        ).rate()
        sofr_index.addFixing(fixing_date, fixing_rate)

    # Create swap
    swap = ql.VanillaSwap(
        swap_type_ql,
        notional,
        fixed_schedule,
        fixed_rate,
        ql.Actual360(),  # fixed leg day count
        floating_schedule,
        sofr_index,
        0.0,  # floating spread
        ql.Actual360(),  # floating leg day count
    )

    # Set pricing engine with OIS discounting
    discount_handle = ql.YieldTermStructureHandle(ois_curve)
    engine = ql.DiscountingSwapEngine(discount_handle)
    swap.setPricingEngine(engine)

    return swap


def _bump_curve(
    curve: ql.YieldTermStructure,
    bump_size: float,
    eval_date: ql.Date,
) -> ql.YieldTermStructure:
    """Apply parallel shift to a curve for sensitivity calculation.

    Args:
        curve: Base QuantLib YieldTermStructure
        bump_size: Parallel shift amount (e.g., 0.0001 for 1bp)
        eval_date: Evaluation date

    Returns:
        Bumped QuantLib YieldTermStructure
    """
    # Create spread handle for parallel shift
    spread_handle = ql.QuoteHandle(ql.SimpleQuote(bump_size))

    # Apply parallel shift
    bumped_curve = ql.ZeroSpreadedTermStructure(
        ql.YieldTermStructureHandle(curve),
        spread_handle
    )
    bumped_curve.enableExtrapolation()

    return bumped_curve
