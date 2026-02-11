"""Tranche waterfall engine for structured products.

Distributes cash flows through a priority-of-payments waterfall structure.
Supports generic CLO/CDO structures with senior, mezzanine, and equity tranches.

Complex deal-specific waterfalls require per-deal customization.
"""
from __future__ import annotations

from typing import Dict, Any, List


def apply_waterfall(
    cashflows: List[Dict[str, Any]],
    tranches: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Allocate cashflows across tranches by priority (senior-first waterfall).

    Args:
        cashflows: List of dicts with {period, interest, principal} for each payment date.
        tranches: List of dicts with {tranche_id, priority, notional, coupon}.
                  Priority 1 = most senior (paid first).

    Returns:
        Dict mapping tranche_id to list of allocated cashflows.
        Each tranche's cashflow includes: period, interest, principal, shortfall, excess.

    Example:
        >>> cashflows = [
        ...     {'period': 1, 'interest': 5.0, 'principal': 10.0},
        ...     {'period': 2, 'interest': 4.5, 'principal': 10.0}
        ... ]
        >>> tranches = [
        ...     {'tranche_id': 'A', 'priority': 1, 'notional': 80, 'coupon': 0.04},
        ...     {'tranche_id': 'B', 'priority': 2, 'notional': 20, 'coupon': 0.08}
        ... ]
        >>> result = apply_waterfall(cashflows, tranches)
        >>> 'A' in result and 'B' in result
        True
    """
    # Sort tranches by priority (lower number = higher priority)
    sorted_tranches = sorted(tranches, key=lambda t: t.get('priority', 999))

    # Initialize result dict: tranche_id -> list of cashflows
    result: Dict[str, List[Dict[str, Any]]] = {
        tranche['tranche_id']: [] for tranche in sorted_tranches
    }

    # Track outstanding notional for each tranche (for principal allocation)
    outstanding = {
        tranche['tranche_id']: float(tranche['notional'])
        for tranche in sorted_tranches
    }

    # Allocate each period's cashflows
    for cf in cashflows:
        period = cf.get('period', 0)
        available_interest = float(cf.get('interest', 0.0))
        available_principal = float(cf.get('principal', 0.0))

        # Allocate interest payments by priority
        for tranche in sorted_tranches:
            tranche_id = tranche['tranche_id']
            coupon = float(tranche.get('coupon', 0.0))
            notional = outstanding[tranche_id]

            # Calculate interest due for this tranche
            # Simplified: annual coupon, assume period = 1 year
            interest_due = notional * coupon

            # Allocate available interest
            interest_paid = min(interest_due, available_interest)
            shortfall_interest = max(0.0, interest_due - interest_paid)
            available_interest -= interest_paid

            # Store allocated interest (principal allocated in next loop)
            if tranche_id not in result:
                result[tranche_id] = []

            result[tranche_id].append({
                'period': period,
                'interest': interest_paid,
                'principal': 0.0,  # Will be filled in principal allocation
                'shortfall': shortfall_interest,
                'excess': 0.0,  # Will be filled if junior tranche
            })

        # Allocate principal payments by priority
        for idx, tranche in enumerate(sorted_tranches):
            tranche_id = tranche['tranche_id']
            notional = outstanding[tranche_id]

            # Allocate available principal to pay down notional
            principal_paid = min(notional, available_principal)
            available_principal -= principal_paid

            # Update outstanding notional
            outstanding[tranche_id] -= principal_paid

            # Update the cashflow record for this period
            # (Already created in interest allocation loop)
            for cf_record in result[tranche_id]:
                if cf_record['period'] == period:
                    cf_record['principal'] = principal_paid
                    break

        # Any remaining cash goes to equity tranche (most junior)
        if available_interest > 0 or available_principal > 0:
            # Allocate excess to most junior tranche
            junior_tranche_id = sorted_tranches[-1]['tranche_id']
            for cf_record in result[junior_tranche_id]:
                if cf_record['period'] == period:
                    cf_record['excess'] = available_interest + available_principal
                    break

    return result


def run_waterfall(
    collateral_flows: List[Dict[str, Any]],
    waterfall_definition: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """Run cash flows through a waterfall structure.

    Wrapper around apply_waterfall with more flexible input format.

    Args:
        collateral_flows: Aggregate cash flows from underlying collateral.
        waterfall_definition: Waterfall rules with tranche priorities and triggers.

    Returns:
        Dict mapping tranche_id to list of distributed cash flows.
    """
    tranches = waterfall_definition.get('tranches', [])
    return apply_waterfall(collateral_flows, tranches)
