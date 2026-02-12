"""Risk-Adjusted Return on Capital (RAROC)."""
from __future__ import annotations


def raroc(revenue: float, expected_loss: float, operating_cost: float, economic_capital: float) -> float:
    """Calculate RAROC.

    RAROC = (Revenue - EL - OpCost) / Economic Capital
    """
    if economic_capital == 0:
        raise ValueError("Economic capital cannot be zero")
    return (revenue - expected_loss - operating_cost) / economic_capital
