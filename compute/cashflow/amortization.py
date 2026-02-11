"""Amortization schedule computation.

Supports level pay, bullet, custom, and interest-only amortization types.
Uses standard PMT formula for level pay calculations.
"""
from __future__ import annotations

from typing import Dict, List
import math


def level_pay_schedule(
    principal: float,
    annual_rate: float,
    num_periods: int,
    frequency: int = 12
) -> List[Dict]:
    """Generate level-pay amortization schedule.

    Calculates constant payment using PMT formula:
    pmt = principal * (r * (1+r)^n) / ((1+r)^n - 1)

    Args:
        principal: Initial principal amount (must be positive).
        annual_rate: Annual interest rate as decimal (e.g., 0.05 for 5%).
        num_periods: Total number of payment periods.
        frequency: Payments per year (12=monthly, 4=quarterly, 2=semiannual).

    Returns:
        List of payment dicts with keys: period, payment, principal, interest, remaining_balance.

    Raises:
        ValueError: If inputs are invalid (non-positive values).

    Example:
        >>> schedule = level_pay_schedule(100000, 0.05, 360, 12)  # 30-year mortgage
        >>> schedule[0]['payment']  # ~536.82
        >>> schedule[-1]['remaining_balance']  # ~0.0
    """
    # Input validation
    if principal <= 0:
        raise ValueError(f"Principal must be positive, got {principal}")
    if annual_rate < 0:
        raise ValueError(f"Annual rate must be non-negative, got {annual_rate}")
    if num_periods <= 0:
        raise ValueError(f"Number of periods must be positive, got {num_periods}")
    if frequency <= 0:
        raise ValueError(f"Frequency must be positive, got {frequency}")

    # Calculate periodic rate
    periodic_rate = annual_rate / frequency

    # Handle zero interest rate edge case (simple equal principal payments)
    if periodic_rate == 0:
        payment_amount = principal / num_periods
        schedule = []
        remaining = principal
        for period in range(1, num_periods + 1):
            principal_payment = payment_amount
            interest_payment = 0.0
            remaining -= principal_payment
            # Avoid floating point negative zeros
            remaining = max(0.0, remaining)

            schedule.append({
                'period': period,
                'payment': payment_amount,
                'principal': principal_payment,
                'interest': interest_payment,
                'remaining_balance': remaining
            })
        return schedule

    # Calculate level payment using PMT formula
    # PMT = P * [r * (1+r)^n] / [(1+r)^n - 1]
    discount_factor = math.pow(1 + periodic_rate, num_periods)
    payment_amount = principal * (periodic_rate * discount_factor) / (discount_factor - 1)

    # Generate amortization schedule
    schedule = []
    remaining_balance = principal

    for period in range(1, num_periods + 1):
        # Interest = remaining balance * periodic rate
        interest_payment = remaining_balance * periodic_rate

        # Principal = total payment - interest
        principal_payment = payment_amount - interest_payment

        # Update remaining balance
        remaining_balance -= principal_payment

        # Handle floating point precision on final period
        if period == num_periods:
            remaining_balance = 0.0

        schedule.append({
            'period': period,
            'payment': payment_amount,
            'principal': principal_payment,
            'interest': interest_payment,
            'remaining_balance': max(0.0, remaining_balance)  # Avoid negative zero
        })

    return schedule


def bullet_schedule(
    principal: float,
    annual_rate: float,
    num_periods: int,
    frequency: int = 12
) -> List[Dict]:
    """Generate bullet amortization schedule (interest-only with principal at maturity).

    Args:
        principal: Principal amount (paid at maturity).
        annual_rate: Annual interest rate as decimal.
        num_periods: Total number of payment periods.
        frequency: Payments per year (12=monthly, 4=quarterly, 2=semiannual).

    Returns:
        List of payment dicts. All periods have zero principal payment except last.

    Example:
        >>> schedule = bullet_schedule(100000, 0.05, 40, 2)  # 20-year semiannual
        >>> schedule[0]['principal']  # 0.0
        >>> schedule[-1]['principal']  # 100000.0
    """
    # Input validation
    if principal <= 0:
        raise ValueError(f"Principal must be positive, got {principal}")
    if annual_rate < 0:
        raise ValueError(f"Annual rate must be non-negative, got {annual_rate}")
    if num_periods <= 0:
        raise ValueError(f"Number of periods must be positive, got {num_periods}")
    if frequency <= 0:
        raise ValueError(f"Frequency must be positive, got {frequency}")

    # Calculate periodic interest payment
    periodic_rate = annual_rate / frequency
    interest_payment = principal * periodic_rate

    schedule = []

    for period in range(1, num_periods + 1):
        if period < num_periods:
            # Interest-only periods
            schedule.append({
                'period': period,
                'payment': interest_payment,
                'principal': 0.0,
                'interest': interest_payment,
                'remaining_balance': principal
            })
        else:
            # Final period: interest + principal
            schedule.append({
                'period': period,
                'payment': interest_payment + principal,
                'principal': principal,
                'interest': interest_payment,
                'remaining_balance': 0.0
            })

    return schedule


def custom_schedule(cashflow_specs: List[Dict]) -> List[Dict]:
    """Generate custom amortization schedule from explicit cashflow specifications.

    Accepts explicit principal and interest payments for each period.
    Validates that the schedule is complete and calculates remaining balances.

    Args:
        cashflow_specs: List of dicts with keys: period, principal, interest.
                       Must cover all periods from 1 to max period.

    Returns:
        List of payment dicts with remaining_balance calculated.

    Raises:
        ValueError: If periods are missing, not sequential, or principal is negative.

    Example:
        >>> specs = [
        ...     {'period': 1, 'principal': 1000, 'interest': 50},
        ...     {'period': 2, 'principal': 1000, 'interest': 45},
        ...     {'period': 3, 'principal': 1000, 'interest': 40},
        ... ]
        >>> schedule = custom_schedule(specs)
        >>> schedule[0]['remaining_balance']  # 2000.0
    """
    if not cashflow_specs:
        raise ValueError("Cashflow specifications cannot be empty")

    # Sort by period to handle out-of-order inputs
    specs_sorted = sorted(cashflow_specs, key=lambda x: x['period'])

    # Validate period sequence (must be 1, 2, 3, ..., N)
    expected_period = 1
    for spec in specs_sorted:
        if spec['period'] != expected_period:
            raise ValueError(
                f"Missing or duplicate period: expected {expected_period}, got {spec['period']}"
            )
        expected_period += 1

        # Validate non-negative values
        if spec.get('principal', 0) < 0:
            raise ValueError(f"Principal cannot be negative in period {spec['period']}")
        if spec.get('interest', 0) < 0:
            raise ValueError(f"Interest cannot be negative in period {spec['period']}")

    # Calculate total principal to determine starting balance
    total_principal = sum(spec.get('principal', 0) for spec in specs_sorted)

    # Generate schedule with remaining balance calculations
    schedule = []
    remaining_balance = total_principal

    for spec in specs_sorted:
        principal_payment = spec.get('principal', 0)
        interest_payment = spec.get('interest', 0)

        schedule.append({
            'period': spec['period'],
            'payment': principal_payment + interest_payment,
            'principal': principal_payment,
            'interest': interest_payment,
            'remaining_balance': remaining_balance - principal_payment
        })

        remaining_balance -= principal_payment

    return schedule
