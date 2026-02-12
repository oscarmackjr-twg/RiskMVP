"""FX analytics: forward points, cross rates, triangulation.

Stub - to be implemented with proper FX forward point calculation.
"""
from __future__ import annotations

from typing import Dict


def fx_forward_rate(spot: float, df_domestic: float, df_foreign: float) -> float:
    """Calculate FX forward rate using covered interest rate parity.

    F = S * (DF_foreign / DF_domestic)
    """
    if df_domestic == 0:
        raise ValueError("Domestic discount factor cannot be zero")
    return spot * (df_foreign / df_domestic)


def fx_forward_points(spot: float, forward: float) -> float:
    """Calculate forward points (pips)."""
    return forward - spot


def cross_rate(pair1_spot: float, pair2_spot: float) -> float:
    """Calculate cross rate from two USD-based pairs.

    E.g., EURGBP = EURUSD / GBPUSD
    """
    if pair2_spot == 0:
        raise ValueError("Second pair spot cannot be zero")
    return pair1_spot / pair2_spot


def triangulate(rates: Dict[str, float], base: str, term: str) -> float:
    """Triangulate an FX rate through USD.

    Stub for complex FX triangulation logic.
    """
    raise NotImplementedError("FX triangulation not yet implemented")
