"""Spread duration calculation."""
from __future__ import annotations


def calculate_spread_duration(pv_base: float, pv_spread_up: float, spread_shock_bps: float = 25.0) -> float:
    """Calculate spread duration (sensitivity to credit spread changes).

    Spread duration = (PV_base - PV_spread_up) / (PV_base * spread_shock)

    Measures sensitivity to credit spread changes.
    Similar to modified duration but for spread risk.

    Args:
        pv_base: Base case present value
        pv_spread_up: Present value after spread INCREASE by spread_shock_bps
        spread_shock_bps: Size of spread shock in basis points (default 25 bps)

    Returns:
        Spread duration (positive for typical bonds)
    """
    if pv_base <= 0:
        raise ValueError("Base PV must be positive")
    if spread_shock_bps <= 0:
        raise ValueError("Spread shock must be positive")

    shock = spread_shock_bps / 10000.0
    return (pv_base - pv_spread_up) / (pv_base * shock)


def spread_duration(pv_base: float, pv_spread_bumped: float, shock_bps: float = 25.0) -> float:
    """Legacy alias for calculate_spread_duration. Deprecated.

    Use calculate_spread_duration instead.
    """
    return calculate_spread_duration(pv_base, pv_spread_bumped, shock_bps)
