"""Duration calculations: Macaulay, Modified, Effective."""
from __future__ import annotations

from typing import List, Dict, Any


def macaulay_duration(cashflows: List[Dict[str, Any]], ytm: float, frequency: int = 2) -> float:
    """Calculate Macaulay duration from cash flows and yield-to-maturity.

    Macaulay duration is the weighted average time to cashflow receipt.

    Formula: MacD = sum(t * PV(CF_t)) / sum(PV(CF_t))
    where PV(CF_t) = CF_t / (1 + ytm/frequency)^(t*frequency)

    Args:
        cashflows: List of cashflows with 'year_fraction' and 'payment' keys
        ytm: Yield to maturity (annualized)
        frequency: Compounding frequency (2 = semi-annual, default)

    Returns:
        Macaulay duration in years
    """
    if not cashflows:
        return 0.0

    total_pv = 0.0
    weighted_time = 0.0

    for cf in cashflows:
        t = cf.get('year_fraction', 0.0)
        payment = cf.get('payment', 0.0)

        if payment == 0.0:
            continue

        # Calculate present value: PV = CF / (1 + ytm/freq)^(t*freq)
        discount_factor = (1.0 + ytm / frequency) ** (t * frequency)
        pv = payment / discount_factor

        total_pv += pv
        weighted_time += t * pv

    if total_pv == 0:
        return 0.0

    return weighted_time / total_pv


def modified_duration(macaulay_dur: float, ytm: float, frequency: int = 2) -> float:
    """Calculate Modified duration from Macaulay duration.

    ModD = MacD / (1 + ytm/frequency)
    """
    return macaulay_dur / (1.0 + ytm / frequency)


def effective_duration(pv_down: float, pv_up: float, pv_base: float, shock_bps: float = 50.0) -> float:
    """Calculate Effective duration using parallel rate shifts.

    EffD = (PV_down - PV_up) / (2 * PV_base * shock)

    Args:
        pv_down: Present value after rates DOWN by shock_bps
        pv_up: Present value after rates UP by shock_bps
        pv_base: Base case present value
        shock_bps: Size of parallel shift in basis points (default 50 bps)

    Returns:
        Effective duration in years
    """
    shock = shock_bps / 10000.0
    if pv_base == 0:
        raise ValueError("Base PV cannot be zero")
    return (pv_down - pv_up) / (2.0 * pv_base * shock)


def calculate_all_durations(
    cashflows: List[Dict[str, Any]],
    ytm: float,
    pv_base: float,
    pv_down: float,
    pv_up: float,
    frequency: int = 2,
    shock_bps: float = 50.0,
) -> Dict[str, float]:
    """Calculate all duration types in one call.

    Args:
        cashflows: List of cashflows with 'year_fraction' and 'payment' keys
        ytm: Yield to maturity (annualized)
        pv_base: Base case present value
        pv_down: Present value after rates DOWN by shock_bps
        pv_up: Present value after rates UP by shock_bps
        frequency: Compounding frequency (2 = semi-annual, default)
        shock_bps: Size of parallel shift in basis points (default 50 bps)

    Returns:
        Dict with keys: 'macaulay', 'modified', 'effective'
    """
    mac_dur = macaulay_duration(cashflows, ytm, frequency)
    mod_dur = modified_duration(mac_dur, ytm, frequency)
    eff_dur = effective_duration(pv_down, pv_up, pv_base, shock_bps)

    return {
        'macaulay': mac_dur,
        'modified': mod_dur,
        'effective': eff_dur,
    }
