"""Exposure at Default (EAD) models."""
from __future__ import annotations


def ead_on_balance(outstanding: float) -> float:
    """EAD for on-balance-sheet exposures (drawn amounts)."""
    return outstanding


def ead_off_balance(committed: float, drawn: float, ccf: float = 0.75) -> float:
    """EAD for off-balance-sheet exposures using Credit Conversion Factor.

    EAD = Drawn + CCF * (Committed - Drawn)
    """
    return drawn + ccf * (committed - drawn)
