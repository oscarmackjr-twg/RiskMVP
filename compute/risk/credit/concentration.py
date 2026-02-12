"""Concentration risk metrics."""
from __future__ import annotations

from typing import Dict, List


def herfindahl_index(exposures: List[float]) -> float:
    """Calculate Herfindahl-Hirschman Index for concentration.

    HHI = sum(w_i^2) where w_i = exposure_i / total_exposure
    HHI ranges from 1/N (perfectly diversified) to 1 (single name).
    """
    total = sum(exposures)
    if total == 0:
        return 0.0
    weights = [e / total for e in exposures]
    return sum(w * w for w in weights)


def top_n_concentration(exposures: Dict[str, float], n: int = 10) -> Dict[str, float]:
    """Return top-N exposures and their share of total.

    Returns dict with keys: names, amounts, pct_of_total.
    """
    raise NotImplementedError("Top-N concentration not yet implemented")
