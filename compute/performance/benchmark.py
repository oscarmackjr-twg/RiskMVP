"""Benchmark comparison engine."""
from __future__ import annotations

from typing import Dict, List


def active_return(portfolio_return: float, benchmark_return: float) -> float:
    """Calculate active return (alpha) vs. benchmark."""
    return portfolio_return - benchmark_return


def tracking_error(active_returns: List[float]) -> float:
    """Calculate tracking error (standard deviation of active returns)."""
    raise NotImplementedError("Tracking error calculation not yet implemented")


def information_ratio(active_returns: List[float]) -> float:
    """Calculate information ratio = mean(active return) / tracking error."""
    raise NotImplementedError("Information ratio not yet implemented")
