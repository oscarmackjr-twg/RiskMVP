"""Key rate duration calculation."""
from __future__ import annotations

from typing import Dict, List, Callable


def calculate_key_rate_durations(
    base_pv: float,
    shocked_pvs: Dict[str, float],
    shock_bps: float = 10.0
) -> Dict[str, float]:
    """Calculate key rate durations from shocked PVs.

    Key rate duration measures sensitivity to individual points on yield curve.
    This is the simpler interface where the caller provides pre-shocked PVs.

    Formula for each tenor:
        key_rate_dur[tenor] = (base_pv - shocked_pvs[tenor]) / (base_pv * shock)

    Args:
        base_pv: Base case present value
        shocked_pvs: Dict mapping tenor to PV after shocking that tenor
                    e.g., {'2Y': pv_2y_up, '5Y': pv_5y_up, '10Y': pv_10y_up}
        shock_bps: Size of shock in basis points (default 10 bps)

    Returns:
        Dict mapping tenor to key rate duration contribution

    Note:
        Sum of key rate durations should approximately equal effective duration
        (within 10-15% tolerance validates calculation correctness)

    Supported tenors: '3M', '6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '20Y', '30Y'
    """
    if base_pv <= 0:
        raise ValueError("Base PV must be positive")
    if shock_bps <= 0:
        raise ValueError("Shock must be positive")

    shock = shock_bps / 10000.0
    key_rate_durs = {}

    for tenor, shocked_pv in shocked_pvs.items():
        # KRD = (PV_base - PV_shocked) / (PV_base * shock)
        # Positive KRD means price falls when that tenor rate rises
        krd = (base_pv - shocked_pv) / (base_pv * shock)
        key_rate_durs[tenor] = krd

    return key_rate_durs


def key_rate_durations(
    pricer_fn: Callable,
    base_pv: float,
    market_snapshot: dict,
    key_rate_tenors: List[str],
    shock_bps: float = 10.0,
) -> Dict[str, float]:
    """Calculate key rate durations by shocking individual tenor points.

    This is the advanced interface that takes a pricer function and
    automatically generates shocked PVs for each tenor.

    Integration with pricers:
    - Pricers must support key rate scenarios (shock individual curve nodes)
    - Use QuantLib SpreadedLinearZeroInterpolatedTermStructure to apply
      tenor-specific shocks to base curves
    - Document in pricer code how to construct tenor-specific shock scenarios

    Args:
        pricer_fn: Function that returns PV given a market snapshot.
                  Signature: pricer_fn(market_snapshot) -> float
        base_pv: Base case present value.
        market_snapshot: Market data to shock (must include yield curves).
        key_rate_tenors: Tenor points to shock individually
                        e.g., ['2Y', '5Y', '10Y']
        shock_bps: Size of shock in basis points (default 10 bps).

    Returns:
        Dict mapping tenor -> key rate duration.

    Example:
        >>> def my_pricer(market):
        ...     # Price bond using market data
        ...     return 100.0
        >>> base_pv = my_pricer(base_market)
        >>> tenors = ['2Y', '5Y', '10Y']
        >>> krds = key_rate_durations(my_pricer, base_pv, base_market, tenors, 10.0)
        >>> print(f"Sum of KRDs: {sum(krds.values()):.4f}")
    """
    if base_pv <= 0:
        raise ValueError("Base PV must be positive")
    if not key_rate_tenors:
        raise ValueError("Must specify at least one tenor")

    shocked_pvs = {}

    for tenor in key_rate_tenors:
        # Create a shocked market snapshot for this tenor
        # Caller must implement tenor-specific shock logic in market_snapshot
        # or this function needs to be enhanced with curve manipulation
        shocked_market = _apply_tenor_shock(market_snapshot, tenor, shock_bps)
        shocked_pvs[tenor] = pricer_fn(shocked_market)

    return calculate_key_rate_durations(base_pv, shocked_pvs, shock_bps)


def _apply_tenor_shock(market_snapshot: dict, tenor: str, shock_bps: float) -> dict:
    """Apply tenor-specific shock to market snapshot.

    This is a placeholder implementation. In production, this would:
    1. Extract yield curves from market_snapshot
    2. Create QuantLib SpreadedLinearZeroInterpolatedTermStructure
    3. Apply shock only to the specified tenor node
    4. Return modified market_snapshot

    Args:
        market_snapshot: Original market data
        tenor: Tenor to shock (e.g., '5Y')
        shock_bps: Size of shock in basis points

    Returns:
        Modified market snapshot with tenor-specific shock applied

    Note:
        This is a stub. Production implementation requires:
        - Tenor-to-maturity mapping ('5Y' -> 5 years)
        - Curve node identification
        - QuantLib SpreadedLinearZeroInterpolatedTermStructure construction
        - Proper curve interpolation
    """
    # TODO: Implement actual tenor-specific curve shocking
    # For now, return a copy of the market snapshot
    # Callers should use calculate_key_rate_durations() with pre-computed shocked PVs
    import copy
    return copy.deepcopy(market_snapshot)
