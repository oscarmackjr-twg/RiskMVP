"""Day count conventions using QuantLib.

Provides factory functions for QuantLib DayCounter objects covering all
standard ISDA day count conventions. Uses QuantLib's implementations rather
than hand-rolling date arithmetic.
"""
from __future__ import annotations

import QuantLib as ql
from typing import Dict


# Map convention strings to QuantLib DayCounter constructors
_DAY_COUNT_MAP: Dict[str, callable] = {
    # ACT/360 - Actual/360
    "ACT/360": lambda: ql.Actual360(),
    "ACTUAL/360": lambda: ql.Actual360(),

    # ACT/365 - Actual/365 (Fixed)
    "ACT/365": lambda: ql.Actual365Fixed(),
    "ACTUAL/365": lambda: ql.Actual365Fixed(),
    "ACT/365F": lambda: ql.Actual365Fixed(),

    # ACT/ACT variants
    "ACT/ACT": lambda: ql.ActualActual(ql.ActualActual.ISDA),
    "ACTUAL/ACTUAL": lambda: ql.ActualActual(ql.ActualActual.ISDA),
    "ACT/ACT-ISDA": lambda: ql.ActualActual(ql.ActualActual.ISDA),
    "ACT/ACT-ICMA": lambda: ql.ActualActual(ql.ActualActual.ICMA),
    "ACT/ACT-BOND": lambda: ql.ActualActual(ql.ActualActual.Bond),

    # 30/360 variants
    "30/360": lambda: ql.Thirty360(ql.Thirty360.BondBasis),
    "30/360-US": lambda: ql.Thirty360(ql.Thirty360.USA),
    "30/360-BOND": lambda: ql.Thirty360(ql.Thirty360.BondBasis),
    "30E/360": lambda: ql.Thirty360(ql.Thirty360.European),
    "30E/360-ISDA": lambda: ql.Thirty360(ql.Thirty360.EurobondBasis),
}


def get_day_counter(convention: str) -> ql.DayCounter:
    """Get QuantLib DayCounter for the specified convention.

    Args:
        convention: Day count convention string (case-insensitive).
                   Supported: ACT/360, ACT/365, ACT/ACT, ACT/ACT-ISDA,
                             ACT/ACT-ICMA, 30/360, 30E/360, 30E/360-ISDA.

    Returns:
        QuantLib DayCounter object.

    Raises:
        ValueError: If convention is not supported.

    Example:
        >>> dc = get_day_counter('ACT/360')
        >>> import QuantLib as ql
        >>> yf = dc.yearFraction(ql.Date(1,1,2026), ql.Date(1,4,2026))
        >>> print(f'{yf:.6f}')  # ~0.247222 (89 days / 360)
    """
    convention_upper = convention.upper().strip()

    if convention_upper not in _DAY_COUNT_MAP:
        valid_conventions = ', '.join(sorted(_DAY_COUNT_MAP.keys()))
        raise ValueError(
            f"Unsupported day count convention: '{convention}'. "
            f"Valid options: {valid_conventions}"
        )

    return _DAY_COUNT_MAP[convention_upper]()


def year_fraction(
    start_date: ql.Date,
    end_date: ql.Date,
    convention: str,
    ref_start: ql.Date | None = None,
    ref_end: ql.Date | None = None,
) -> float:
    """Calculate year fraction between two dates using the specified convention.

    Args:
        start_date: Period start date (QuantLib Date).
        end_date: Period end date (QuantLib Date).
        convention: Day count convention string.
        ref_start: Reference period start (for ICMA convention).
        ref_end: Reference period end (for ICMA convention).

    Returns:
        Year fraction as a float.

    Example:
        >>> import QuantLib as ql
        >>> yf = year_fraction(ql.Date(1,1,2026), ql.Date(1,4,2026), 'ACT/360')
        >>> print(f'{yf:.6f}')  # 89/360 = 0.247222
    """
    dc = get_day_counter(convention)

    # ICMA convention requires reference dates for coupon period
    if ref_start and ref_end:
        return dc.yearFraction(start_date, end_date, ref_start, ref_end)
    else:
        return dc.yearFraction(start_date, end_date)


def day_count(start_date: ql.Date, end_date: ql.Date, convention: str) -> int:
    """Count the number of days between two dates using the specified convention.

    Args:
        start_date: Period start date.
        end_date: Period end date.
        convention: Day count convention string.

    Returns:
        Number of days as integer.

    Example:
        >>> import QuantLib as ql
        >>> days = day_count(ql.Date(1,1,2026), ql.Date(1,2,2026), 'ACT/360')
        >>> print(days)  # 31
    """
    dc = get_day_counter(convention)
    return dc.dayCount(start_date, end_date)
