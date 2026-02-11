"""Payment schedule generation engine.

Generates projected cash flow schedules for fixed income instruments
based on their terms, conventions, and amortization type.
Uses QuantLib for date schedule generation with calendar adjustments.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Any

import QuantLib as ql

from compute.quantlib.day_count import get_day_counter
from compute.quantlib.calendar import get_calendar
from compute.cashflow.amortization import (
    level_pay_schedule,
    bullet_schedule,
    custom_schedule
)


def _parse_date(d: str | date) -> date:
    """Parse date from string or date object."""
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def _to_ql_date(d: date) -> ql.Date:
    """Convert Python date to QuantLib Date."""
    return ql.Date(d.day, d.month, d.year)


def _from_ql_date(ql_date: ql.Date) -> date:
    """Convert QuantLib Date to Python date."""
    return date(ql_date.year(), ql_date.month(), ql_date.dayOfMonth())


def _parse_frequency(freq_str: str) -> ql.Frequency:
    """Parse frequency string to QuantLib Frequency."""
    freq_map = {
        'MONTHLY': ql.Monthly,
        'QUARTERLY': ql.Quarterly,
        'SEMIANNUAL': ql.Semiannual,
        'SEMI_ANNUAL': ql.Semiannual,
        'ANNUAL': ql.Annual,
        'ANNUALLY': ql.Annual,
    }
    freq_upper = freq_str.upper().strip()
    if freq_upper not in freq_map:
        raise ValueError(
            f"Unsupported frequency: {freq_str}. "
            f"Valid options: {', '.join(freq_map.keys())}"
        )
    return freq_map[freq_upper]


def _frequency_to_periods_per_year(freq: ql.Frequency) -> int:
    """Convert QuantLib Frequency to periods per year."""
    freq_map = {
        ql.Monthly: 12,
        ql.Quarterly: 4,
        ql.Semiannual: 2,
        ql.Annual: 1,
    }
    return freq_map.get(freq, 1)


def generate_schedule(
    instrument: Dict[str, Any],
    as_of_date: date,
    end_date: date | None = None,
) -> List[Dict[str, Any]]:
    """Generate a payment schedule for an instrument.

    Combines QuantLib date schedule generation with amortization logic
    to produce complete cashflow schedules with principal/interest splits.

    Args:
        instrument: Instrument definition with fields:
            - issue_date: str or date
            - maturity_date: str or date
            - principal: float
            - coupon: float (annual rate as decimal)
            - frequency: str ('MONTHLY', 'QUARTERLY', 'SEMIANNUAL', 'ANNUAL')
            - day_count: str (e.g., 'ACT/360', '30/360')
            - calendar: str (e.g., 'US-GOVT', 'TARGET')
            - amortization_type: str ('LEVEL_PAY', 'BULLET', 'CUSTOM')
            - custom_cashflows: List[Dict] (if amortization_type='CUSTOM')
        as_of_date: Valuation date (only future flows are generated).
        end_date: Optional end date override (default: use maturity_date).

    Returns:
        List of cash flow dicts with fields:
            - period: int
            - pay_date: date
            - principal: float
            - interest: float
            - payment: float (principal + interest)
            - remaining_balance: float
            - year_fraction: float (day count fraction)

    Raises:
        ValueError: If required instrument fields are missing or invalid.

    Example:
        >>> from datetime import date
        >>> instrument = {
        ...     'issue_date': '2020-01-01',
        ...     'maturity_date': '2030-01-01',
        ...     'principal': 100000,
        ...     'coupon': 0.05,
        ...     'frequency': 'SEMIANNUAL',
        ...     'day_count': 'ACT/360',
        ...     'calendar': 'US-GOVT',
        ...     'amortization_type': 'BULLET'
        ... }
        >>> schedule = generate_schedule(instrument, date(2026, 2, 11))
        >>> len(schedule)  # 8 future payments (semiannual from 2026 to 2030)
    """
    # Parse dates
    issue_date = _parse_date(instrument.get('issue_date', as_of_date))
    maturity_date = _parse_date(instrument.get('maturity_date'))

    if end_date:
        termination_date = _parse_date(end_date)
    else:
        termination_date = maturity_date

    # Validate dates
    if termination_date <= as_of_date:
        # Maturity already past - return empty schedule
        return []

    # Parse instrument parameters
    principal = float(instrument.get('principal', 0))
    if principal <= 0:
        raise ValueError(f"Principal must be positive, got {principal}")

    coupon = float(instrument.get('coupon', 0))
    frequency_str = instrument.get('frequency', 'SEMIANNUAL')
    day_count_str = instrument.get('day_count', 'ACT/360')
    calendar_str = instrument.get('calendar', 'US-GOVT')
    amortization_type = instrument.get('amortization_type', 'BULLET').upper()

    # Convert to QuantLib objects
    ql_issue = _to_ql_date(issue_date)
    ql_maturity = _to_ql_date(termination_date)
    ql_as_of = _to_ql_date(as_of_date)

    frequency = _parse_frequency(frequency_str)
    calendar = get_calendar(calendar_str)
    day_counter = get_day_counter(day_count_str)

    # Generate QuantLib date schedule
    # Use Schedule constructor directly for better control
    try:
        ql_schedule = ql.Schedule(
            ql_issue,                      # effectiveDate
            ql_maturity,                   # terminationDate
            ql.Period(frequency),          # tenor
            calendar,                      # calendar
            ql.ModifiedFollowing,          # convention
            ql.ModifiedFollowing,          # terminationDateConvention
            ql.DateGeneration.Backward,    # rule (backward from maturity)
            False                          # endOfMonth
        )
    except Exception as e:
        raise ValueError(f"Failed to create QuantLib schedule: {e}")

    # Extract payment dates from QuantLib schedule
    pay_dates = []
    for i in range(len(ql_schedule)):
        ql_date = ql_schedule[i]
        py_date = _from_ql_date(ql_date)
        # Only include dates after as_of_date
        if py_date > as_of_date:
            pay_dates.append(py_date)

    if not pay_dates:
        # All payment dates are in the past
        return []

    num_payments = len(pay_dates)
    periods_per_year = _frequency_to_periods_per_year(frequency)

    # Generate amortization schedule based on type
    if amortization_type == 'LEVEL_PAY':
        # Calculate total periods from issue to maturity
        ql_full_schedule = ql.Schedule(
            ql_issue,
            ql_maturity,
            ql.Period(frequency),
            calendar,
            ql.ModifiedFollowing,
            ql.ModifiedFollowing,
            ql.DateGeneration.Backward,
            False
        )

        total_periods = len(ql_full_schedule) - 1  # Exclude start date

        amort_schedule = level_pay_schedule(
            principal=principal,
            annual_rate=coupon,
            num_periods=total_periods,
            frequency=periods_per_year
        )

        # Map to future payments only
        # Calculate which period we're starting from
        start_period = total_periods - num_payments + 1
        amort_schedule = amort_schedule[start_period - 1:]  # Adjust to 0-based index

    elif amortization_type == 'BULLET':
        amort_schedule = bullet_schedule(
            principal=principal,
            annual_rate=coupon,
            num_periods=num_payments,
            frequency=periods_per_year
        )

    elif amortization_type == 'CUSTOM':
        custom_cashflows = instrument.get('custom_cashflows', [])
        if not custom_cashflows:
            raise ValueError("CUSTOM amortization requires 'custom_cashflows' field")

        amort_schedule = custom_schedule(custom_cashflows)

        # Filter to future periods only
        future_periods = []
        for cf in amort_schedule:
            period_idx = cf['period'] - 1
            if period_idx < len(pay_dates):
                future_periods.append(cf)
        amort_schedule = future_periods

    else:
        raise ValueError(
            f"Unsupported amortization type: {amortization_type}. "
            "Valid options: LEVEL_PAY, BULLET, CUSTOM"
        )

    # Merge date schedule with amortization schedule
    cashflow_schedule = []
    prev_date = as_of_date

    for idx, pay_date in enumerate(pay_dates):
        if idx >= len(amort_schedule):
            # This shouldn't happen, but handle gracefully
            break

        amort = amort_schedule[idx]

        # Calculate year fraction using day count convention
        ql_prev = _to_ql_date(prev_date)
        ql_pay = _to_ql_date(pay_date)
        year_frac = day_counter.yearFraction(ql_prev, ql_pay)

        cashflow = {
            'period': idx + 1,
            'pay_date': pay_date,
            'principal': amort['principal'],
            'interest': amort['interest'],
            'payment': amort['payment'],
            'remaining_balance': amort['remaining_balance'],
            'year_fraction': year_frac
        }

        cashflow_schedule.append(cashflow)
        prev_date = pay_date

    return cashflow_schedule
