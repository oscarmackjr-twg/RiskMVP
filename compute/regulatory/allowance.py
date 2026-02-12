"""Allowance for Credit Losses (ACL) calculation."""
from __future__ import annotations

from typing import Dict, List, Any


def compute_allowance(
    ecl_results: List[Dict[str, Any]],
    qualitative_adjustments: Dict[str, float] | None = None,
) -> Dict[str, float]:
    """Compute total allowance for credit losses.

    Combines quantitative ECL results with qualitative (Q-factor) adjustments.

    Args:
        ecl_results: ECL results by segment/pool.
        qualitative_adjustments: Optional Q-factor adjustments by category.

    Returns:
        Dict with total_allowance, quantitative, qualitative components.
    """
    raise NotImplementedError("Allowance calculation not yet implemented")
