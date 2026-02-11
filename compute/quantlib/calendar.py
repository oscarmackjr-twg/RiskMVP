"""Business day conventions and holiday calendars using QuantLib.

Provides factory functions for QuantLib Calendar objects with accurate
holiday rules for major financial centers. Uses QuantLib's implementations
rather than maintaining custom holiday lists.
"""
from __future__ import annotations

import QuantLib as ql
from typing import Dict


# Map calendar names to QuantLib Calendar constructors
_CALENDAR_MAP: Dict[str, callable] = {
    # United States calendars
    "US": lambda: ql.UnitedStates(ql.UnitedStates.Settlement),
    "US-SETTLEMENT": lambda: ql.UnitedStates(ql.UnitedStates.Settlement),
    "US-GOVT": lambda: ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    "US-GOVERNMENTBOND": lambda: ql.UnitedStates(ql.UnitedStates.GovernmentBond),
    "US-NYSE": lambda: ql.UnitedStates(ql.UnitedStates.NYSE),
    "US-NERC": lambda: ql.UnitedStates(ql.UnitedStates.NERC),

    # European calendars
    "UK": lambda: ql.UnitedKingdom(ql.UnitedKingdom.Settlement),
    "UK-SETTLEMENT": lambda: ql.UnitedKingdom(ql.UnitedKingdom.Settlement),
    "UK-EXCHANGE": lambda: ql.UnitedKingdom(ql.UnitedKingdom.Exchange),
    "UK-METALS": lambda: ql.UnitedKingdom(ql.UnitedKingdom.Metals),
    "TARGET": lambda: ql.TARGET(),  # Trans-European Automated Real-time Gross Settlement

    # Asian calendars
    "JAPAN": lambda: ql.Japan(),
    "TOKYO": lambda: ql.Japan(),
    "CHINA": lambda: ql.China(ql.China.SSE),
    "HONGKONG": lambda: ql.HongKong(ql.HongKong.HKEx),

    # Other major centers
    "CANADA": lambda: ql.Canada(ql.Canada.Settlement),
    "CANADA-TSX": lambda: ql.Canada(ql.Canada.TSX),
    "AUSTRALIA": lambda: ql.Australia(),

    # Utility calendars
    "NULLCALENDAR": lambda: ql.NullCalendar(),  # No holidays (every day is business day)
    "WEEKENDSONLY": lambda: ql.WeekendsOnly(),  # Only weekends are non-business days
}


def get_calendar(name: str) -> ql.Calendar:
    """Get QuantLib Calendar for the specified financial center.

    Args:
        name: Calendar name (case-insensitive).
              Supported: US, US-GOVT, US-NYSE, UK, TARGET (Eurozone),
                        JAPAN, CHINA, HONGKONG, CANADA, AUSTRALIA,
                        NULLCALENDAR, WEEKENDSONLY.

    Returns:
        QuantLib Calendar object with accurate holiday rules.

    Raises:
        ValueError: If calendar name is not supported.

    Example:
        >>> cal = get_calendar('US-GOVT')
        >>> import QuantLib as ql
        >>> is_holiday = not cal.isBusinessDay(ql.Date(1, 1, 2026))
        >>> print(is_holiday)  # True (New Year's Day)
    """
    name_upper = name.upper().strip()

    if name_upper not in _CALENDAR_MAP:
        valid_calendars = ', '.join(sorted(_CALENDAR_MAP.keys()))
        raise ValueError(
            f"Unsupported calendar: '{name}'. "
            f"Valid options: {valid_calendars}"
        )

    return _CALENDAR_MAP[name_upper]()


def is_business_day(date: ql.Date, calendar: ql.Calendar | str) -> bool:
    """Check if a date is a business day (not weekend, not holiday).

    Args:
        date: QuantLib Date to check.
        calendar: QuantLib Calendar object or calendar name string.

    Returns:
        True if date is a business day, False otherwise.

    Example:
        >>> import QuantLib as ql
        >>> is_bday = is_business_day(ql.Date(1, 1, 2026), 'US-GOVT')
        >>> print(is_bday)  # False (New Year's Day)
    """
    if isinstance(calendar, str):
        calendar = get_calendar(calendar)

    return calendar.isBusinessDay(date)


def is_holiday(date: ql.Date, calendar: ql.Calendar | str) -> bool:
    """Check if a date is a holiday.

    Args:
        date: QuantLib Date to check.
        calendar: QuantLib Calendar object or calendar name string.

    Returns:
        True if date is a holiday, False otherwise.

    Example:
        >>> import QuantLib as ql
        >>> is_hol = is_holiday(ql.Date(4, 7, 2026), 'US-GOVT')
        >>> print(is_hol)  # True (Independence Day - Saturday, observed Friday 7/3)
    """
    return not is_business_day(date, calendar)


def adjust_date(
    date: ql.Date,
    calendar: ql.Calendar | str,
    convention: ql.BusinessDayConvention = ql.Following,
) -> ql.Date:
    """Adjust a date according to a business day convention.

    Args:
        date: Date to adjust.
        calendar: Calendar to use for adjustment (object or name string).
        convention: Business day convention (Following, ModifiedFollowing, etc.).
                   Default is Following.

    Returns:
        Adjusted business day.

    Example:
        >>> import QuantLib as ql
        >>> adjusted = adjust_date(ql.Date(4, 7, 2026), 'US-GOVT', ql.Following)
        >>> # July 4, 2026 is Saturday (holiday), adjusted to Monday July 6, 2026
    """
    if isinstance(calendar, str):
        calendar = get_calendar(calendar)

    return calendar.adjust(date, convention)


def advance_date(
    date: ql.Date,
    period: ql.Period,
    calendar: ql.Calendar | str,
    convention: ql.BusinessDayConvention = ql.Following,
    end_of_month: bool = False,
) -> ql.Date:
    """Advance a date by a given period, adjusting for business days.

    Args:
        date: Starting date.
        period: Period to advance (e.g., ql.Period('3M'), ql.Period('1Y')).
        calendar: Calendar to use (object or name string).
        convention: Business day convention for adjustment.
        end_of_month: If True, preserve end-of-month dates.

    Returns:
        Advanced and adjusted date.

    Example:
        >>> import QuantLib as ql
        >>> advanced = advance_date(
        ...     ql.Date(15, 1, 2026),
        ...     ql.Period('3M'),
        ...     'US-GOVT',
        ...     ql.ModifiedFollowing
        ... )
        >>> # Advances to April 15, 2026
    """
    if isinstance(calendar, str):
        calendar = get_calendar(calendar)

    return calendar.advance(date, period, convention, end_of_month)


def business_days_between(
    start_date: ql.Date,
    end_date: ql.Date,
    calendar: ql.Calendar | str,
    include_first: bool = True,
    include_last: bool = False,
) -> int:
    """Count business days between two dates.

    Args:
        start_date: Start of period.
        end_date: End of period.
        calendar: Calendar to use (object or name string).
        include_first: Include start_date in count if it's a business day.
        include_last: Include end_date in count if it's a business day.

    Returns:
        Number of business days.

    Example:
        >>> import QuantLib as ql
        >>> bdays = business_days_between(
        ...     ql.Date(1, 1, 2026),
        ...     ql.Date(31, 1, 2026),
        ...     'US-GOVT'
        ... )
    """
    if isinstance(calendar, str):
        calendar = get_calendar(calendar)

    return calendar.businessDaysBetween(start_date, end_date, include_first, include_last)
