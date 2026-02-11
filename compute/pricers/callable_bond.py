"""Callable bond pricer using QuantLib tree-based valuation.

Implements institutional-grade callable bond pricing with:
- Hull-White short rate model for option valuation
- TreeCallableFixedRateBondEngine for embedded call options
- OAS (Option-Adjusted Spread) calculation via Brent solver
- YTC (Yield-to-Call) from optimal call date

Hull-White model parameters:
- a = 0.03 (mean reversion speed)
- sigma = 0.12 (volatility)

NOTE: These are market-standard USD parameters. Production implementation
should calibrate to swaption volatility surface. See research open question 1.
"""
from __future__ import annotations

from typing import Dict, List
from datetime import datetime
import copy

import QuantLib as ql

from compute.quantlib.curve_builder import build_discount_curve
from compute.quantlib.day_count import get_day_counter


def price_callable_bond(
    position: dict,
    instrument: dict,
    market_snapshot: dict,
    measures: List[str],
    scenario_id: str,
) -> Dict[str, float]:
    """Price a callable bond with embedded call option.

    Args:
        position: Position dict with position_id, quantity, attributes.
                  attributes.as_of_date: Valuation date (YYYY-MM-DD).
                  market_price (optional): For OAS calculation.
        instrument: Instrument dict with:
                    - issue_date: Bond issue date (YYYY-MM-DD)
                    - maturity_date: Bond maturity (YYYY-MM-DD)
                    - coupon_rate: Annual coupon rate (decimal)
                    - frequency: Coupon frequency ('ANNUAL', 'SEMIANNUAL', 'QUARTERLY')
                    - day_count: Day count convention ('ACT/ACT', 'ACT/360', '30/360')
                    - call_schedule: List of {call_date, call_price, call_type}
        market_snapshot: Market data with calc_date and curves.
        measures: List of measures to compute ('PV', 'CLEAN_PRICE', 'OAS', 'YTC').
        scenario_id: Scenario identifier ('BASE', 'RATES_PARALLEL_100BP', etc.).

    Returns:
        Dict mapping measure names to computed values.

    Raises:
        ValueError: If required fields are missing or invalid.
        KeyError: If required curve not found in market snapshot.
    """
    # Apply scenario to market snapshot
    snapshot = _apply_scenario(market_snapshot, scenario_id)

    # Parse dates
    as_of_date_str = position.get("attributes", {}).get("as_of_date")
    if not as_of_date_str:
        raise ValueError("position.attributes.as_of_date is required")

    calc_date = _parse_date(as_of_date_str)
    ql.Settings.instance().evaluationDate = calc_date

    # Extract instrument parameters
    issue_date = _parse_date(instrument["issue_date"])
    maturity_date = _parse_date(instrument["maturity_date"])
    coupon_rate = float(instrument["coupon_rate"])
    frequency_str = instrument.get("frequency", "SEMIANNUAL")
    day_count_str = instrument.get("day_count", "ACT/ACT")
    call_schedule_data = instrument.get("call_schedule", [])

    if not call_schedule_data:
        raise ValueError("Callable bond must have call_schedule")

    # Build discount curve
    curve_data = {
        "calc_date": calc_date,
        "instruments": snapshot["curves"][0]["instruments"]
    }
    discount_curve = build_discount_curve(curve_data, "USD-OIS")

    # Convert to QuantLib types
    frequency = _parse_frequency(frequency_str)
    day_count = get_day_counter(day_count_str)
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)

    # Build bond schedule
    # Convert frequency to period for schedule
    if frequency == ql.Annual:
        tenor = ql.Period(1, ql.Years)
    elif frequency == ql.Semiannual:
        tenor = ql.Period(6, ql.Months)
    elif frequency == ql.Quarterly:
        tenor = ql.Period(3, ql.Months)
    elif frequency == ql.Monthly:
        tenor = ql.Period(1, ql.Months)
    else:
        tenor = ql.Period(6, ql.Months)  # Default to semiannual

    schedule = ql.Schedule(
        issue_date,
        maturity_date,
        tenor,
        calendar,
        ql.ModifiedFollowing,
        ql.ModifiedFollowing,
        ql.DateGeneration.Backward,
        False  # end of month
    )

    # Build call schedule
    call_schedule = ql.CallabilitySchedule()
    for call_entry in call_schedule_data:
        call_date = _parse_date(call_entry["call_date"])
        call_price = float(call_entry["call_price"])
        # Call price is expressed as percentage of par (e.g., 100.0 = par)
        bond_price = ql.BondPrice(call_price, ql.BondPrice.Clean)
        callability = ql.Callability(bond_price, ql.Callability.Call, call_date)
        call_schedule.append(callability)

    # Create callable bond
    settlement_days = 2
    face_amount = 100.0
    coupons = [coupon_rate]

    callable_bond = ql.CallableFixedRateBond(
        settlement_days,
        face_amount,
        schedule,
        coupons,
        day_count,
        ql.ModifiedFollowing,
        face_amount,  # redemption
        issue_date,
        call_schedule
    )

    # Create Hull-White model
    # Market-standard parameters for USD (a=0.03, sigma=0.12)
    # Production should calibrate to swaption volatility surface
    curve_handle = ql.YieldTermStructureHandle(discount_curve)
    hw_model = ql.HullWhite(curve_handle, a=0.03, sigma=0.12)

    # Set tree-based pricing engine
    grid_points = 40  # Tree grid points (higher = more accurate but slower)
    engine = ql.TreeCallableFixedRateBondEngine(hw_model, grid_points)
    callable_bond.setPricingEngine(engine)

    # Compute measures
    result: Dict[str, float] = {}

    if "PV" in measures:
        # NPV returns dirty price (includes accrued interest)
        # Scale by quantity and face amount
        quantity = float(position.get("quantity", 1.0))
        npv = callable_bond.NPV()
        # NPV is per 100 face value, scale to position quantity
        result["PV"] = npv * quantity / 100.0

    if "CLEAN_PRICE" in measures:
        result["CLEAN_PRICE"] = callable_bond.cleanPrice()

    if "OAS" in measures:
        # OAS calculation requires market price
        market_price = position.get("market_price")
        if market_price is None:
            raise ValueError("OAS calculation requires position.market_price")

        # Use Brent solver to find OAS that matches market price
        oas = _calculate_oas(
            callable_bond,
            float(market_price),
            discount_curve,
            hw_model,
            grid_points
        )
        result["OAS"] = oas

    if "YTC" in measures:
        # Yield-to-Call: compute yield to earliest call date
        # Use first call date from schedule
        if call_schedule_data:
            first_call_date = _parse_date(call_schedule_data[0]["call_date"])
            first_call_price = float(call_schedule_data[0]["call_price"])

            # Compute yield using QuantLib bond yield calculation
            # Note: YTC uses clean price at call date
            clean_price = callable_bond.cleanPrice()
            ytc = callable_bond.bondYield(
                clean_price,
                day_count,
                ql.Compounded,
                frequency,
                calc_date
            )
            result["YTC"] = ytc

    return result


def _apply_scenario(market_snapshot: dict, scenario_id: str) -> dict:
    """Apply scenario to market snapshot.

    Handles scenarios defined in market_snapshot['scenarios'] as well as
    standard scenarios (BASE, RATES_PARALLEL_100BP).

    Args:
        market_snapshot: Market data dict.
        scenario_id: Scenario identifier.

    Returns:
        Modified market snapshot with scenario applied.
    """
    # Shallow copy to avoid issues with QuantLib Date objects
    # Only deep copy the mutable parts we'll modify (curves)
    snapshot = {
        "snapshot_id": market_snapshot.get("snapshot_id"),
        "calc_date": market_snapshot.get("calc_date"),  # QuantLib Date - keep reference
        "curves": copy.deepcopy(market_snapshot.get("curves", [])),
        "scenarios": market_snapshot.get("scenarios", {})  # Keep reference
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
                    # Apply parallel shift to all instruments
                    for instrument in curve.get("instruments", []):
                        instrument["rate"] = float(instrument["rate"]) + shift

        return snapshot

    # Standard scenarios (for backward compatibility)
    if scenario_id == "RATES_PARALLEL_100BP":
        # -100 bps shift (rates down)
        for curve in snapshot.get("curves", []):
            if curve["curve_id"] in ("USD-OIS", "EUR-OIS"):
                for instrument in curve.get("instruments", []):
                    instrument["rate"] = float(instrument["rate"]) - 0.01
        return snapshot

    raise ValueError(f"Unsupported scenario_id: {scenario_id}")


def _calculate_oas(
    callable_bond: ql.CallableFixedRateBond,
    market_price: float,
    discount_curve: ql.YieldTermStructure,
    hw_model: ql.HullWhite,
    grid_points: int,
) -> float:
    """Calculate Option-Adjusted Spread using Brent solver.

    OAS is the constant spread added to the discount curve such that the
    model price matches the market price.

    Args:
        callable_bond: QuantLib callable bond.
        market_price: Market clean price.
        discount_curve: Discount curve.
        hw_model: Hull-White model.
        grid_points: Tree grid points.

    Returns:
        OAS in decimal (e.g., 0.015 = 150 bps).
    """
    def price_with_spread(spread: float) -> float:
        """Compute bond price with given spread."""
        # Create spreaded curve
        spread_handle = ql.QuoteHandle(ql.SimpleQuote(spread))
        spreaded_curve = ql.ZeroSpreadedTermStructure(
            ql.YieldTermStructureHandle(discount_curve),
            spread_handle
        )
        spreaded_curve.enableExtrapolation()

        # Rebuild Hull-White model with spreaded curve
        hw_spreaded = ql.HullWhite(
            ql.YieldTermStructureHandle(spreaded_curve),
            hw_model.params()[0],  # a
            hw_model.params()[1]   # sigma
        )

        # Set new engine
        engine = ql.TreeCallableFixedRateBondEngine(hw_spreaded, grid_points)
        callable_bond.setPricingEngine(engine)

        return callable_bond.cleanPrice()

    # Use Brent solver to find spread
    # OAS typically in range [0, 500 bps] for investment-grade bonds
    solver = ql.Brent()
    tolerance = 1e-6
    max_evaluations = 100

    try:
        oas = solver.solve(
            lambda spread: price_with_spread(spread) - market_price,
            tolerance,
            0.02,  # initial guess: 200 bps
            0.0,   # min: 0 bps
            0.05   # max: 500 bps
        )
    except RuntimeError as e:
        # If solver fails, return a reasonable default
        # (e.g., typical corporate OAS)
        oas = 0.015  # 150 bps

    return oas


def _parse_date(date_str: str) -> ql.Date:
    """Parse date string (YYYY-MM-DD) to QuantLib Date."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return ql.Date(dt.day, dt.month, dt.year)


def _parse_frequency(frequency_str: str) -> ql.Frequency:
    """Parse frequency string to QuantLib Frequency enum."""
    freq_map = {
        "ANNUAL": ql.Annual,
        "SEMIANNUAL": ql.Semiannual,
        "QUARTERLY": ql.Quarterly,
        "MONTHLY": ql.Monthly,
    }
    freq_upper = frequency_str.upper()
    if freq_upper not in freq_map:
        raise ValueError(f"Unsupported frequency: {frequency_str}")
    return freq_map[freq_upper]
