"""Performance ratios: Sharpe, Sortino, max drawdown."""
from __future__ import annotations

from typing import List


def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio."""
    raise NotImplementedError("Sharpe ratio not yet implemented")


def sortino_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sortino ratio (downside deviation only)."""
    raise NotImplementedError("Sortino ratio not yet implemented")


def max_drawdown(cumulative_returns: List[float]) -> float:
    """Calculate maximum drawdown from peak."""
    raise NotImplementedError("Max drawdown not yet implemented")
