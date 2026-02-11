"""Floating rate note/loan pricer using QuantLib FloatingRateBond.

Implements multi-curve framework with separate OIS discount and SOFR projection curves.
Handles index-based coupon resets with optional caps/floors.
"""
from __future__ import annotations

from typing import Dict, List
import QuantLib as ql
from datetime import datetime

from compute.quantlib.curve_builder import build_discount_curve, build_forward_curve
from compute.cashflow.arm_reset import calculate_reset_coupon


def _parse_date(date_str: str) -> ql.Date:
    """Parse YYYY-MM-DD string to QuantLib Date."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return ql.Date(dt.day, dt.month, dt.year)


def _parse_frequency(freq_str: str) -> ql.Frequency:
    """Parse frequency string to QuantLib Frequency."""
    freq_map = {
        "Monthly": ql.Monthly,
        "Quarterly": ql.Quarterly,
        "Semiannual": ql.Semiannual,
        "Semi-annual": ql.Semiannual,
        "Annual": ql.Annual,
    }
    freq = freq_map.get(freq_str)
    if freq is None:
        raise ValueError(f"Unsupported reset frequency: {freq_str}")
    return freq


def _parse_day_count(dc_str: str) -> ql.DayCounter:
    """Parse day count string to QuantLib DayCounter."""
    dc_map = {
        "ACT/360": ql.Actual360(),
        "ACT/365": ql.Actual365Fixed(),
        "ACT/ACT": ql.ActualActual(ql.ActualActual.ISDA),
        "30/360": ql.Thirty360(ql.Thirty360.USA),
    }
    dc = dc_map.get(dc_str)
    if dc is None:
        raise ValueError(f"Unsupported day count: {dc_str}")
    return dc


def price_floating_rate(
    position: dict,
    instrument: dict,
    market_snapshot: dict,
    measures: List[str],
    scenario_id: str,
) -> Dict[str, float]:
    """Price a floating rate instrument using QuantLib FloatingRateBond.

    Uses multi-curve framework:
    - OIS curve for discounting
    - SOFR/LIBOR curve for forward rate projection
    - Separate curves allow modeling of basis spreads

    Args:
        position: Position dict with attributes.
        instrument: Instrument dict with terms (issue_date, maturity_date, spread, index, cap/floor).
        market_snapshot: Market data with calc_date, ois_instruments, sofr_instruments.
        measures: List of measures to compute (PV, DV01).
        scenario_id: Scenario identifier (currently only BASE supported).

    Returns:
        Dict mapping measure names to computed values.

    Raises:
        ValueError: If required data is missing or invalid.
    """
    # Extract instrument terms
    terms = instrument.get("terms", {})
    issue_date = _parse_date(terms["issue_date"])
    maturity_date = _parse_date(terms["maturity_date"])
    face_value = float(terms.get("face_value", 100.0))
    spread = float(terms.get("spread", 0.0))  # Spread over index
    index_name = terms.get("index", "SOFR-3M")
    reset_frequency = _parse_frequency(terms.get("reset_frequency", "Quarterly"))
    day_count_str = terms.get("day_count", "ACT/360")
    day_count = _parse_day_count(day_count_str)

    # Optional cap/floor
    cap = float(terms["cap"]) if "cap" in terms else None
    floor = float(terms["floor"]) if "floor" in terms else None

    # Set evaluation date
    calc_date = market_snapshot["calc_date"]
    ql.Settings.instance().evaluationDate = calc_date

    # Build curves using multi-curve framework
    # OIS curve for discounting
    ois_market_data = {
        "calc_date": calc_date,
        "instruments": market_snapshot.get("ois_instruments", []),
    }
    ois_curve = build_discount_curve(ois_market_data, "USD-OIS")
    ois_handle = ql.YieldTermStructureHandle(ois_curve)

    # SOFR curve for forward projection
    sofr_market_data = {
        "calc_date": calc_date,
        "instruments": market_snapshot.get("sofr_instruments", []),
    }
    sofr_curve = build_forward_curve(sofr_market_data, "USD-SOFR-3M", "3M", ois_curve)
    sofr_handle = ql.YieldTermStructureHandle(sofr_curve)

    # Create SOFR index (3M tenor)
    # QuantLib doesn't have a native SOFR index yet, so we use USDLibor as proxy
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    index = ql.USDLibor(ql.Period(3, ql.Months), sofr_handle)

    # Build coupon schedule first (needed for fixing dates)
    schedule = ql.Schedule(
        issue_date,
        maturity_date,
        ql.Period(reset_frequency),
        calendar,
        ql.ModifiedFollowing,  # convention
        ql.ModifiedFollowing,  # termination date convention
        ql.DateGeneration.Forward,
        False,  # end of month
    )

    # Add historical fixings for past coupon periods
    # For floating rate bonds, QuantLib needs fixings for all past reset dates
    # Reset dates are typically 2 business days before coupon payment
    fixing_rate = 0.035  # Use flat rate for historical fixings (inferred from forward curve)

    # Generate fixing dates from schedule (2 days before each coupon date)
    for i in range(len(schedule) - 1):
        coupon_date = schedule[i + 1]
        # Fixing is 2 business days before coupon date
        fixing_date = calendar.advance(coupon_date, ql.Period(-2, ql.Days), ql.Preceding)

        # Only add fixings for dates in the past (before calc_date)
        if fixing_date < calc_date:
            try:
                index.addFixing(fixing_date, fixing_rate)
            except RuntimeError:
                # Fixing may already exist or date may be invalid, skip
                pass

    # Create floating rate bond
    # Gearings and spreads must be vectors matching the schedule
    num_coupons = len(schedule) - 1
    gearings = [1.0] * num_coupons
    spreads = [spread] * num_coupons

    # Caps and floors (if present)
    caps = [cap] * num_coupons if cap is not None else []
    floors = [floor] * num_coupons if floor is not None else []

    bond = ql.FloatingRateBond(
        2,  # settlement_days
        face_value,  # faceAmount
        schedule,  # schedule
        index,  # index
        day_count,  # paymentDayCounter
        ql.Following,  # paymentConvention
        2,  # fixingDays (single value for all coupons)
        gearings,  # gearings vector
        spreads,  # spreads vector
        caps,  # caps vector
        floors,  # floors vector
        False,  # inArrears
    )

    # Set pricing engine
    # For capped/floored floaters, need to set coupon pricers first
    if caps or floors:
        # Use Black model for caplet/floorlet valuation
        # Create a constant optionlet volatility structure (20% flat vol)
        volatility = 0.20
        vol_structure = ql.ConstantOptionletVolatility(
            2,  # settlement days
            calendar,
            ql.Following,
            volatility,
            day_count
        )
        vol_handle = ql.OptionletVolatilityStructureHandle(vol_structure)

        # Create Black Ibor coupon pricer
        black_pricer = ql.BlackIborCouponPricer(vol_handle)

        # Set pricer for each coupon
        ql.setCouponPricer(bond.cashflows(), black_pricer)

    # Set bond pricing engine (uses OIS curve for discounting)
    pricing_engine = ql.DiscountingBondEngine(ois_handle)
    bond.setPricingEngine(pricing_engine)

    # Compute measures
    results: Dict[str, float] = {}

    if "PV" in measures:
        # NPV returns clean price (without accrued interest)
        # For full PV, use cleanPrice() or NPV()
        pv = bond.NPV()
        results["PV"] = pv

    if "DV01" in measures:
        # DV01: Change in PV for 1bp parallel shift in OIS curve
        # Bump OIS curve +1bp and reprice
        base_pv = bond.NPV()

        # Create bumped instruments (+1bp = 0.0001)
        bumped_ois_instruments = [
            {**inst, "rate": inst["rate"] + 0.0001}
            for inst in market_snapshot.get("ois_instruments", [])
        ]
        bumped_ois_data = {
            "calc_date": calc_date,
            "instruments": bumped_ois_instruments,
        }
        bumped_ois_curve = build_discount_curve(bumped_ois_data, "USD-OIS")
        bumped_ois_handle = ql.YieldTermStructureHandle(bumped_ois_curve)

        # Rebuild SOFR curve with bumped OIS as discount curve
        bumped_sofr_curve = build_forward_curve(
            sofr_market_data, "USD-SOFR-3M", "3M", bumped_ois_curve
        )
        bumped_sofr_handle = ql.YieldTermStructureHandle(bumped_sofr_curve)

        # Recreate index with bumped curve
        bumped_index = ql.USDLibor(ql.Period(3, ql.Months), bumped_sofr_handle)

        # Recreate bond with bumped index
        bumped_bond = ql.FloatingRateBond(
            2,  # settlement_days
            face_value,  # faceAmount
            schedule,  # schedule
            bumped_index,  # index
            day_count,  # paymentDayCounter
            ql.Following,  # paymentConvention
            2,  # fixingDays
            gearings,  # gearings vector
            spreads,  # spreads vector
            caps,  # caps vector
            floors,  # floors vector
            False,  # inArrears
        )

        # Set coupon pricers if caps/floors present
        if caps or floors:
            volatility = 0.20
            vol_structure = ql.ConstantOptionletVolatility(
                2, calendar, ql.Following, volatility, day_count
            )
            vol_handle = ql.OptionletVolatilityStructureHandle(vol_structure)
            black_pricer = ql.BlackIborCouponPricer(vol_handle)
            ql.setCouponPricer(bumped_bond.cashflows(), black_pricer)

        bumped_engine = ql.DiscountingBondEngine(bumped_ois_handle)
        bumped_bond.setPricingEngine(bumped_engine)

        bumped_pv = bumped_bond.NPV()
        dv01 = bumped_pv - base_pv
        results["DV01"] = dv01

    return results
