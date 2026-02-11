"""Convexity calculation."""
from __future__ import annotations


def calculate_convexity(pv_base: float, pv_down: float, pv_up: float, shock_bps: float = 50.0) -> float:
    """Calculate convexity using parallel rate shifts.

    Convexity = (PV_up + PV_down - 2*PV_base) / (PV_base * shock^2)
    where shock = shock_bps / 10000

    Measures curvature of price-yield relationship.
    Higher convexity = more favorable price behavior for large rate changes.

    Args:
        pv_base: Base case present value
        pv_down: Present value after rates DOWN by shock_bps
        pv_up: Present value after rates UP by shock_bps
        shock_bps: Size of parallel shift in basis points (default 50 bps)

    Returns:
        Convexity (positive for typical bonds)
    """
    if pv_base <= 0:
        raise ValueError("Base PV must be positive")
    if shock_bps <= 0:
        raise ValueError("Shock must be positive")

    shock = shock_bps / 10000.0
    return (pv_down + pv_up - 2.0 * pv_base) / (pv_base * shock * shock)


def effective_convexity(pv_down: float, pv_up: float, pv_base: float, shock_bps: float = 50.0) -> float:
    """Legacy alias for calculate_convexity. Deprecated.

    Use calculate_convexity instead.
    """
    return calculate_convexity(pv_base, pv_down, pv_up, shock_bps)
