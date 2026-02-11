"""Adjustable rate mortgage/loan reset logic.

Handles rate resets for ARM instruments based on index + margin with caps/floors.
"""
from __future__ import annotations

from typing import Dict, Any, List


def calculate_reset_coupon(
    index_rate: float,
    spread: float,
    cap: float | None = None,
    floor: float | None = None,
    day_count_fraction: float = 0.25,
) -> float:
    """Calculate coupon rate for floating-rate instrument reset.

    Computes the coupon rate for a floating-rate instrument reset period
    by adding the spread to the index rate and applying any caps/floors.

    Args:
        index_rate: Reference rate (e.g., 3M SOFR) as decimal (0.035 = 3.5%)
        spread: Fixed spread in decimal (0.015 = 150 bps)
        cap: Optional cap rate (decimal). If provided, coupon cannot exceed this rate.
        floor: Optional floor rate (decimal). If provided, coupon cannot fall below this rate.
        day_count_fraction: Accrual period (0.25 for quarterly, 0.5 for semi-annual).
                            Currently informational; actual payment = coupon_rate * day_count_fraction * notional.

    Returns:
        Coupon rate as decimal (annual rate, not period payment).

    Examples:
        >>> # 3.5% SOFR + 150 bps spread = 5.0% coupon
        >>> calculate_reset_coupon(0.035, 0.015)
        0.05

        >>> # With 4.5% cap: 3.5% + 150 bps = 5.0%, capped to 4.5%
        >>> calculate_reset_coupon(0.035, 0.015, cap=0.045)
        0.045

        >>> # With 2% floor: 0.5% + 150 bps = 2.0%, floor doesn't bind
        >>> calculate_reset_coupon(0.005, 0.015, floor=0.02)
        0.02
    """
    # Calculate base coupon: index + spread
    coupon_rate = index_rate + spread

    # Apply cap if present (limit upside)
    if cap is not None:
        coupon_rate = min(coupon_rate, cap)

    # Apply floor if present (limit downside)
    if floor is not None:
        coupon_rate = max(coupon_rate, floor)

    return coupon_rate


def project_arm_resets(
    instrument: Dict[str, Any],
    rate_paths: List[List[float]],
    index_name: str = "SOFR",
) -> List[Dict[str, Any]]:
    """Project ARM rate resets under given interest rate paths.

    Args:
        instrument: ARM terms including margin, caps, floors, reset frequency.
        rate_paths: Projected index rate paths (one path per scenario).
        index_name: Reference rate index.

    Returns:
        List of reset events with effective rate, cap/floor applied.
    """
    raise NotImplementedError("ARM reset projection not yet implemented")
