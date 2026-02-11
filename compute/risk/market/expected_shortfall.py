"""Expected Shortfall (CVaR) calculation."""
from __future__ import annotations

from typing import List
import numpy as np


def calculate_expected_shortfall(
    returns: List[float],
    confidence_level: float = 0.95,
) -> float:
    """Calculate Expected Shortfall (Conditional VaR).

    ES (CVaR) = mean of returns beyond VaR threshold.
    ES is a coherent risk measure and always ≥ VaR.

    Args:
        returns: Return observations (as decimals, e.g. 0.01 = 1%).
        confidence_level: Confidence level (e.g. 0.95, 0.99).

    Returns:
        Expected Shortfall amount (positive number representing average tail loss).

    Raises:
        ValueError: If returns list is empty or confidence_level out of range.

    Example:
        >>> returns = np.random.normal(-0.0005, 0.02, 1000).tolist()
        >>> es = calculate_expected_shortfall(returns, 0.95)
        >>> print(f"ES 95%: {es:.4f}")
    """
    if not returns:
        raise ValueError("Returns list cannot be empty")
    if not (0 < confidence_level < 1):
        raise ValueError(f"Confidence level must be between 0 and 1, got {confidence_level}")

    # Sort returns ascending (worst losses first)
    sorted_returns = sorted(returns)

    # Identify VaR cutoff at (1 - confidence_level) percentile
    cutoff_index = int((1 - confidence_level) * len(sorted_returns))

    # Ensure at least one observation in tail
    if cutoff_index == 0:
        cutoff_index = 1

    # Calculate mean of worst returns (tail)
    tail_returns = sorted_returns[:cutoff_index]

    if not tail_returns:
        # Edge case: no tail returns
        return -sorted_returns[0]

    mean_tail_loss = np.mean(tail_returns)

    # ES is positive loss magnitude
    return -mean_tail_loss


# Legacy function name for backward compatibility
def expected_shortfall(
    pnl_series: List[float],
    confidence_level: float = 0.95,
) -> float:
    """Calculate Expected Shortfall (Conditional VaR) - legacy name.

    ES = average loss beyond the VaR threshold.

    Args:
        pnl_series: P&L observations (historical or simulated).
        confidence_level: Confidence level.

    Returns:
        Expected Shortfall amount.
    """
    return calculate_expected_shortfall(pnl_series, confidence_level)
