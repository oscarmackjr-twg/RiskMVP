"""Default and recovery modeling.

Projects defaults and recovery rates for credit-risky instruments.
"""
from __future__ import annotations

from typing import Dict, Any, List


def apply_default_model(
    schedule: List[Dict[str, Any]],
    pd_curve: List[float],
    lgd: float,
    ead_pct: float = 1.0
) -> List[Dict[str, Any]]:
    """Apply default and recovery model to a cashflow schedule.

    Simplified credit model using marginal PD per period.
    Note: Full credit modeling with survival curves is Phase 4 enhancement.

    Args:
        schedule: Base cash flow schedule with 'remaining_principal' field.
        pd_curve: List of marginal probability of default per period (0-1).
        lgd: Loss given default as decimal (e.g., 0.40 = 40% loss).
        ead_pct: Exposure at default as % of remaining principal (default 1.0 = 100%).

    Returns:
        Schedule with 'default_loss' and 'recovery' fields added.
    """
    result = []

    # Clamp LGD to valid range
    lgd = max(0.0, min(1.0, lgd))
    ead_pct = max(0.0, min(1.0, ead_pct))

    for i, cf in enumerate(schedule):
        cf = cf.copy()  # Don't mutate input
        remaining_principal = cf.get('remaining_principal', 0.0)

        # Get PD for this period (default to 0 if curve too short)
        pd = pd_curve[i] if i < len(pd_curve) else 0.0
        pd = max(0.0, min(1.0, pd))  # Clamp to valid range

        # Calculate expected default loss
        exposure_at_default = remaining_principal * ead_pct
        default_amount = exposure_at_default * pd
        loss_amount = default_amount * lgd
        recovery_amount = default_amount * (1.0 - lgd)

        # Add fields to cashflow
        cf['default_loss'] = loss_amount
        cf['recovery'] = recovery_amount

        # Reduce principal cashflow by default amount
        if 'scheduled_principal' in cf:
            cf['scheduled_principal'] = cf['scheduled_principal'] - default_amount
        elif 'principal' in cf:
            cf['principal'] = cf['principal'] - default_amount

        # Update remaining principal
        cf['remaining_principal'] = remaining_principal - default_amount

        result.append(cf)

    return result


def project_defaults(
    schedule: List[Dict[str, Any]],
    pd_curve: List[float],
    lgd: float,
    recovery_lag_months: int = 6,
) -> List[Dict[str, Any]]:
    """Apply default and recovery assumptions to a cash flow schedule.

    This is a wrapper around apply_default_model() for backward compatibility.

    Args:
        schedule: Base cash flow schedule.
        pd_curve: Monthly marginal default probabilities.
        lgd: Loss given default (0-1).
        recovery_lag_months: Months between default and recovery (currently unused).

    Returns:
        Adjusted schedule with default losses and recovery flows.
    """
    # For MVP, recovery is immediate (same period). Recovery lag is Phase 4 enhancement.
    return apply_default_model(schedule, pd_curve, lgd, ead_pct=1.0)


def constant_default_rate(annual_cdr: float) -> float:
    """Convert annual CDR to monthly default rate."""
    return 1.0 - (1.0 - annual_cdr) ** (1.0 / 12.0)
