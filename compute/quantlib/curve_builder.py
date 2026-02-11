"""Multi-curve construction engine using QuantLib.

Implements bootstrapping of discount curves, forward curves, and basis curves
using QuantLib's PiecewiseYieldCurve with proven interpolation algorithms.

Supports multi-curve framework (OIS discounting + tenor-specific projection curves).
"""
from __future__ import annotations

from typing import Dict, List, Any, Tuple
import QuantLib as ql


def build_discount_curve(market_data: Dict[str, Any], curve_id: str) -> ql.YieldTermStructure:
    """Bootstrap a discount curve from market instruments using QuantLib.

    Uses PiecewiseLogCubicDiscount for institutional-grade curve construction.
    Supports deposits and swaps as input instruments.

    Args:
        market_data: Dict with 'calc_date' (ql.Date) and 'instruments' (list of dicts).
                     Each instrument has: type, rate, tenor, fixing_days.
        curve_id: Identifier for the curve (e.g., 'USD-OIS', 'USD-SOFR').

    Returns:
        QuantLib YieldTermStructure with extrapolation enabled.

    Raises:
        ValueError: If required instruments are missing or invalid.

    Example:
        >>> import QuantLib as ql
        >>> market_data = {
        ...     'calc_date': ql.Date(15, 1, 2026),
        ...     'instruments': [
        ...         {'type': 'DEPOSIT', 'rate': 0.025, 'tenor': '3M', 'fixing_days': 2},
        ...         {'type': 'SWAP', 'rate': 0.030, 'tenor': '2Y', 'fixing_days': 2}
        ...     ]
        ... }
        >>> curve = build_discount_curve(market_data, 'USD-OIS')
        >>> df = curve.discount(ql.Date(15, 4, 2026))
    """
    if 'calc_date' not in market_data:
        raise ValueError("market_data must contain 'calc_date' (QuantLib.Date)")
    if 'instruments' not in market_data or not market_data['instruments']:
        raise ValueError("market_data must contain non-empty 'instruments' list")

    calc_date = market_data['calc_date']
    ql.Settings.instance().evaluationDate = calc_date

    # Determine appropriate calendar and day count convention
    # Default to US Government bond market conventions
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    day_count = ql.Actual360()

    # Build rate helpers from market instruments
    helpers = []
    for instrument in market_data['instruments']:
        try:
            rate = instrument['rate']
            tenor_str = instrument['tenor']
            fixing_days = instrument.get('fixing_days', 2)

            # Parse tenor (e.g., '3M', '2Y')
            period = _parse_tenor(tenor_str)
            quote = ql.QuoteHandle(ql.SimpleQuote(rate))

            if instrument['type'] == 'DEPOSIT':
                helper = ql.DepositRateHelper(
                    quote,
                    period,
                    fixing_days,
                    calendar,
                    ql.ModifiedFollowing,
                    False,  # end of month
                    day_count
                )
            elif instrument['type'] == 'SWAP':
                # Simplified swap helper (assumes fixed-for-floating)
                # In production, would parameterize fixed/float legs
                index = ql.USDLibor(ql.Period('3M'))
                helper = ql.SwapRateHelper(
                    quote,
                    period,
                    calendar,
                    ql.Semiannual,  # fixed leg frequency
                    ql.ModifiedFollowing,
                    ql.Actual360(),  # fixed leg day count
                    index
                )
            else:
                raise ValueError(f"Unsupported instrument type: {instrument['type']}")

            helpers.append(helper)

        except KeyError as e:
            raise ValueError(f"Instrument missing required field {e}: {instrument}")
        except Exception as e:
            raise ValueError(f"Failed to create helper for instrument {instrument}: {e}")

    if not helpers:
        raise ValueError(f"No valid helpers created for curve {curve_id}")

    # Bootstrap curve using PiecewiseLogCubicDiscount
    # LogCubic interpolation is standard for discount factors (maintains positivity)
    try:
        curve = ql.PiecewiseLogCubicDiscount(
            calc_date,
            helpers,
            day_count
        )
        curve.enableExtrapolation()

        # Force evaluation to fail-fast on bad data
        # (QuantLib uses lazy evaluation by default)
        _ = curve.discount(calc_date)

    except RuntimeError as e:
        raise ValueError(f"Failed to bootstrap curve {curve_id}: {e}")

    return curve


def build_forward_curve(
    market_data: Dict[str, Any],
    curve_id: str,
    tenor: str,
    discount_curve: ql.YieldTermStructure | None = None,
) -> ql.YieldTermStructure:
    """Build a forward rate curve for a given tenor (e.g., 3M SOFR, 6M LIBOR).

    Supports multi-curve framework: separate discount and projection curves.
    If discount_curve is provided, uses it for discounting (OIS discounting).

    Args:
        market_data: Dict with 'calc_date' and 'instruments'.
        curve_id: Curve identifier (e.g., 'USD-SOFR-3M').
        tenor: Forward rate tenor (e.g., '3M', '6M').
        discount_curve: Optional discount curve for multi-curve setup.

    Returns:
        QuantLib YieldTermStructure for forward projection.

    Example:
        >>> ois_curve = build_discount_curve(ois_data, 'USD-OIS')
        >>> fwd_curve = build_forward_curve(sofr_data, 'USD-SOFR-3M', '3M', ois_curve)
    """
    if 'calc_date' not in market_data:
        raise ValueError("market_data must contain 'calc_date'")

    calc_date = market_data['calc_date']
    ql.Settings.instance().evaluationDate = calc_date

    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    day_count = ql.Actual360()

    # Create tenor-specific index
    tenor_period = _parse_tenor(tenor)

    # Build helpers for forward curve
    # In multi-curve framework, forward rates come from tenor-specific instruments
    helpers = []
    discount_handle = (
        ql.YieldTermStructureHandle(discount_curve)
        if discount_curve
        else ql.YieldTermStructureHandle()
    )

    for instrument in market_data.get('instruments', []):
        try:
            rate = instrument['rate']
            instrument_tenor = instrument['tenor']
            fixing_days = instrument.get('fixing_days', 2)

            period = _parse_tenor(instrument_tenor)
            quote = ql.QuoteHandle(ql.SimpleQuote(rate))

            # For forward curves, typically use FRA or futures helpers
            # Simplified: use swap helpers with tenor-specific index
            if instrument['type'] in ('SWAP', 'FRA'):
                index = ql.USDLibor(tenor_period)
                helper = ql.SwapRateHelper(
                    quote,
                    period,
                    calendar,
                    ql.Semiannual,
                    ql.ModifiedFollowing,
                    day_count,
                    index,
                    ql.QuoteHandle(),  # spread
                    ql.Period('0D'),  # fwd start
                    discount_handle  # discounting curve
                )
                helpers.append(helper)

        except Exception as e:
            # Skip invalid instruments (forward curve may have subset of discount instruments)
            continue

    if not helpers:
        # If no tenor-specific instruments, fall back to discount curve logic
        return build_discount_curve(market_data, curve_id)

    try:
        curve = ql.PiecewiseLogCubicDiscount(
            calc_date,
            helpers,
            day_count
        )
        curve.enableExtrapolation()
        _ = curve.discount(calc_date)
    except RuntimeError as e:
        raise ValueError(f"Failed to bootstrap forward curve {curve_id}: {e}")

    return curve


def build_basis_curve(
    base_curve: ql.YieldTermStructure,
    basis_spreads: List[Dict[str, Any]],
) -> ql.YieldTermStructure:
    """Apply basis spreads to a base curve using ZeroSpreadedTermStructure.

    Used for cross-currency basis or tenor basis spreads.

    Args:
        base_curve: Base QuantLib YieldTermStructure.
        basis_spreads: List of dicts with 'tenor' and 'spread' (in bps or decimal).

    Returns:
        Modified QuantLib YieldTermStructure with spreads applied.

    Example:
        >>> base = build_discount_curve(market_data, 'EUR-OIS')
        >>> basis = [{'tenor': '1Y', 'spread': 0.0010}, {'tenor': '5Y', 'spread': 0.0015}]
        >>> curve = build_basis_curve(base, basis)
    """
    if not basis_spreads:
        # No spreads to apply, return original curve
        return base_curve

    # For simplicity, apply a flat spread (average of all basis spreads)
    # Production implementation would interpolate spreads across tenors
    spreads = [bs['spread'] for bs in basis_spreads if 'spread' in bs]
    if not spreads:
        return base_curve

    avg_spread = sum(spreads) / len(spreads)

    # Create spread handle
    spread_handle = ql.QuoteHandle(ql.SimpleQuote(avg_spread))

    # Apply spread to base curve
    # ZeroSpreadedTermStructure applies parallel shift to zero rates
    spreaded_curve = ql.ZeroSpreadedTermStructure(
        ql.YieldTermStructureHandle(base_curve),
        spread_handle
    )
    spreaded_curve.enableExtrapolation()

    return spreaded_curve


def _parse_tenor(tenor_str: str) -> ql.Period:
    """Parse tenor string (e.g., '3M', '2Y', '10Y') into QuantLib Period.

    Args:
        tenor_str: Tenor string like '3M', '6M', '1Y', '5Y'.

    Returns:
        QuantLib Period object.

    Raises:
        ValueError: If tenor string is invalid.
    """
    tenor_str = tenor_str.upper().strip()

    if not tenor_str:
        raise ValueError("Tenor string cannot be empty")

    # Extract number and unit
    if tenor_str[-1] in ('D', 'W', 'M', 'Y'):
        unit = tenor_str[-1]
        try:
            value = int(tenor_str[:-1])
        except ValueError:
            raise ValueError(f"Invalid tenor format: {tenor_str}")
    else:
        raise ValueError(f"Invalid tenor unit in: {tenor_str}")

    # Map to QuantLib units
    unit_map = {
        'D': ql.Days,
        'W': ql.Weeks,
        'M': ql.Months,
        'Y': ql.Years,
    }

    return ql.Period(value, unit_map[unit])
