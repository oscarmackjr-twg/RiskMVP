"""Prepayment modeling: CPR, PSA, and custom models.

Projects voluntary prepayment rates for mortgage and loan portfolios.
"""
from __future__ import annotations

from typing import Dict, Any, List


def cpr_to_smm(cpr: float) -> float:
    """Convert annual CPR (Conditional Prepayment Rate) to monthly SMM."""
    return 1.0 - (1.0 - cpr) ** (1.0 / 12.0)


def psa_speed(month: int, psa_multiplier: float = 100.0) -> float:
    """Calculate CPR for a given month under PSA standard.

    PSA 100%: CPR ramps from 0.2% to 6% over 30 months, then flat at 6%.
    PSA multiplier scales linearly (e.g., PSA 200% = double the CPR).
    """
    base_cpr = min(month * 0.002, 0.06)
    return base_cpr * (psa_multiplier / 100.0)


def apply_psa_prepayment(
    schedule: List[Dict[str, Any]],
    psa_speed: float = 100.0
) -> List[Dict[str, Any]]:
    """Apply PSA prepayment model to a cashflow schedule.

    PSA (Public Securities Association) standard model:
    - CPR ramps from 0.2% to 6% over first 30 months
    - Then constant at 6% thereafter
    - PSA multiplier scales the base curve (e.g., PSA 200% = 2x the CPR)

    Args:
        schedule: Base amortization schedule with 'month' and 'remaining_principal' fields.
        psa_speed: PSA multiplier (100.0 = PSA 100%).

    Returns:
        Schedule with 'prepayment' field added to each period.
    """
    result = []

    for cf in schedule:
        cf = cf.copy()  # Don't mutate input
        month = cf.get('month', 0)
        remaining_principal = cf.get('remaining_principal', 0.0)

        # Handle edge cases
        if remaining_principal <= 0.0:
            cf['prepayment'] = 0.0
            result.append(cf)
            continue

        # PSA model: CPR ramps from 0.2% to 6% over 30 months
        base_cpr = min(month * 0.002, 0.06)
        cpr = base_cpr * (psa_speed / 100.0)

        # Clamp to valid range [0, 1]
        cpr = max(0.0, min(1.0, cpr))

        # Convert CPR to SMM (Single Monthly Mortality)
        smm = cpr_to_smm(cpr)

        # Calculate prepayment amount
        prepay_amount = remaining_principal * smm
        cf['prepayment'] = prepay_amount

        # Update remaining principal
        cf['remaining_principal'] = remaining_principal - prepay_amount

        result.append(cf)

    return result


def apply_cpr_prepayment(
    schedule: List[Dict[str, Any]],
    cpr: float
) -> List[Dict[str, Any]]:
    """Apply constant CPR (Conditional Prepayment Rate) to cashflow schedule.

    Constant CPR model applies a uniform prepayment rate to all periods,
    without the PSA ramp-up.

    Args:
        schedule: Base amortization schedule with 'remaining_principal' field.
        cpr: Annual CPR as decimal (e.g., 0.06 = 6% CPR).

    Returns:
        Schedule with 'prepayment' field added to each period.
    """
    result = []

    # Clamp CPR to valid range
    cpr = max(0.0, min(1.0, cpr))

    # Convert to SMM once
    smm = cpr_to_smm(cpr)

    for cf in schedule:
        cf = cf.copy()  # Don't mutate input
        remaining_principal = cf.get('remaining_principal', 0.0)

        # Handle edge case
        if remaining_principal <= 0.0:
            cf['prepayment'] = 0.0
            result.append(cf)
            continue

        # Apply constant prepayment rate
        prepay_amount = remaining_principal * smm
        cf['prepayment'] = prepay_amount

        # Update remaining principal
        cf['remaining_principal'] = remaining_principal - prepay_amount

        result.append(cf)

    return result


def project_prepayments(
    schedule: List[Dict[str, Any]],
    model_type: str,
    parameters: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Apply prepayment model to a cash flow schedule.

    Args:
        schedule: Base amortization schedule.
        model_type: "CPR", "PSA", or "CUSTOM".
        parameters: Model parameters (rate, psa_speed, etc.)

    Returns:
        Adjusted schedule with prepayment cash flows.
    """
    if model_type == "PSA":
        psa_speed = parameters.get("psa_speed", 100.0)
        return apply_psa_prepayment(schedule, psa_speed)
    elif model_type == "CPR":
        cpr = parameters.get("cpr", 0.06)
        return apply_cpr_prepayment(schedule, cpr)
    else:
        raise NotImplementedError(f"Prepayment model '{model_type}' not yet implemented")
