"""Portfolio optimization engine."""
from __future__ import annotations

from typing import Dict, List, Any


def mean_variance_optimize(
    expected_returns: List[float],
    covariance_matrix: List[List[float]],
    constraints: Dict[str, Any] | None = None,
) -> List[float]:
    """Mean-variance portfolio optimization (Markowitz).

    Returns optimal portfolio weights.
    """
    raise NotImplementedError("Mean-variance optimization not yet implemented")


def risk_parity_weights(covariance_matrix: List[List[float]]) -> List[float]:
    """Calculate risk parity portfolio weights."""
    raise NotImplementedError("Risk parity not yet implemented")
