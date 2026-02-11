"""DV01 / PV01 calculation."""
from __future__ import annotations

from typing import List, Dict, Any


def calculate_dv01(price_base: float, price_up_1bp: float) -> float:
    """Calculate DV01 (dollar value of a 1 basis point rate increase).

    DV01 = Price_base - Price_up_1bp

    Measures dollar value of 1 basis point rate increase.
    A positive DV01 means the position loses value when rates rise.

    Args:
        price_base: Base case price/PV
        price_up_1bp: Price/PV after 1bp rate increase

    Returns:
        DV01 (dollar change for 1bp rate increase)
    """
    if price_base == 0:
        raise ValueError("Base price cannot be zero")
    return price_base - price_up_1bp


def calculate_pv01(cashflows: List[Dict[str, Any]], ytm: float, frequency: int = 2) -> float:
    """Calculate PV01 from cashflows and modified duration.

    Alternative calculation from cashflows.
    Can also derive from Modified Duration: PV01 ≈ ModD * PV / 10000

    Args:
        cashflows: List of cashflows with 'year_fraction' and 'payment' keys
        ytm: Yield to maturity (annualized)
        frequency: Compounding frequency (2 = semi-annual, default)

    Returns:
        PV01 (dollar value of 1bp change)
    """
    # Calculate present value and duration-weighted PV
    total_pv = 0.0
    duration_weighted_pv = 0.0

    for cf in cashflows:
        t = cf.get('year_fraction', 0.0)
        payment = cf.get('payment', 0.0)

        if payment == 0.0:
            continue

        # Calculate present value
        discount_factor = (1.0 + ytm / frequency) ** (t * frequency)
        pv = payment / discount_factor

        total_pv += pv
        duration_weighted_pv += t * pv

    if total_pv == 0:
        return 0.0

    # Modified duration = Macaulay / (1 + ytm/freq)
    macaulay_dur = duration_weighted_pv / total_pv
    modified_dur = macaulay_dur / (1.0 + ytm / frequency)

    # PV01 = Modified Duration * PV / 10000
    return modified_dur * total_pv / 10000.0


# Legacy aliases for backward compatibility
def dv01(pv_base: float, pv_bumped: float) -> float:
    """Legacy alias for calculate_dv01. Deprecated."""
    return calculate_dv01(pv_base, pv_bumped)


def pv01(pv_base: float, modified_duration: float) -> float:
    """Approximate PV01 from modified duration.

    PV01 ~= PV * ModD * 0.0001
    """
    return pv_base * modified_duration * 0.0001
