"""Liquidity risk metrics: bid-ask spread, time-to-liquidate, LCR."""
from __future__ import annotations

from typing import Dict, Any


def calculate_bid_ask_spread(bid_price: float, ask_price: float) -> float:
    """Calculate bid-ask spread as percentage of mid-price.

    Spread = (ask - bid) / mid_price

    Args:
        bid_price: Bid price
        ask_price: Ask price

    Returns:
        Spread as decimal (e.g., 0.005 = 50 bps)

    Example:
        >>> spread = calculate_bid_ask_spread(99.5, 100.5)
        >>> print(f"Spread: {spread:.4f} ({spread * 10000:.1f} bps)")
        Spread: 0.0100 (100.0 bps)
    """
    if bid_price <= 0 or ask_price <= 0:
        raise ValueError("Prices must be positive")
    if ask_price < bid_price:
        raise ValueError("Ask price must be >= bid price")

    mid_price = (bid_price + ask_price) / 2.0
    if mid_price == 0:
        return 0.0

    return (ask_price - bid_price) / mid_price


def estimate_time_to_liquidate(
    position_size: float,
    avg_daily_volume: float,
    participation_rate: float = 0.10
) -> float:
    """Estimate time to liquidate a position.

    Time = position_size / (avg_daily_volume * participation_rate)

    Args:
        position_size: Position size (in shares or notional)
        avg_daily_volume: Average daily trading volume
        participation_rate: Maximum participation rate (default 10%)

    Returns:
        Time to liquidate in days

    Example:
        >>> days = estimate_time_to_liquidate(100000, 500000, 0.10)
        >>> print(f"Time to liquidate: {days:.1f} days")
        Time to liquidate: 2.0 days
    """
    if position_size < 0:
        raise ValueError("Position size must be non-negative")
    if avg_daily_volume <= 0:
        return float('inf')
    if not (0 < participation_rate <= 1):
        raise ValueError("Participation rate must be between 0 and 1")

    daily_capacity = avg_daily_volume * participation_rate
    return position_size / daily_capacity


def calculate_lcr(liquid_assets: float, net_cash_outflows_30d: float) -> float:
    """Calculate Liquidity Coverage Ratio (Basel III).

    LCR = liquid_assets / net_cash_outflows_30d

    Basel III requirement: LCR >= 100%

    Args:
        liquid_assets: High-quality liquid assets
        net_cash_outflows_30d: Net cash outflows over 30-day stress period

    Returns:
        LCR ratio (e.g., 1.20 = 120%)

    Example:
        >>> lcr = calculate_lcr(120_000_000, 100_000_000)
        >>> print(f"LCR: {lcr:.2%}")
        LCR: 120.00%
    """
    if liquid_assets < 0:
        raise ValueError("Liquid assets must be non-negative")
    if net_cash_outflows_30d <= 0:
        # If no net outflows, LCR is effectively infinite (fully covered)
        return float('inf')

    return liquid_assets / net_cash_outflows_30d


# Legacy function names for backward compatibility
def bid_ask_cost(mid_price: float, bid: float, ask: float, quantity: float) -> float:
    """Calculate liquidation cost from bid-ask spread.

    Cost = quantity * (ask - bid) / 2
    """
    return quantity * (ask - bid) / 2.0


def time_to_liquidate(position_value: float, avg_daily_volume: float, participation_rate: float = 0.1) -> float:
    """Estimate days to liquidate a position (legacy name).

    Days = Position / (ADV * Participation Rate)
    """
    return estimate_time_to_liquidate(position_value, avg_daily_volume, participation_rate)
