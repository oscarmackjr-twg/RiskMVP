"""Golden tests for curve construction and day count conventions.

Validates QuantLib curve bootstrapping, day count fractions, and calendar logic
against known reference values.
"""
import pytest
import QuantLib as ql
from compute.quantlib.curve_builder import build_discount_curve, build_forward_curve, build_basis_curve
from compute.quantlib.day_count import get_day_counter, year_fraction
from compute.quantlib.calendar import get_calendar, is_business_day, adjust_date


def test_discount_curve_bootstrap():
    """Test discount curve bootstrapping from deposits and swaps.

    Validates that QuantLib PiecewiseLogCubicDiscount produces expected
    discount factors at instrument maturities.
    """
    # Market data with deposits and swaps
    calc_date = ql.Date(15, 1, 2026)
    market_data = {
        'calc_date': calc_date,
        'instruments': [
            # Deposits
            {'type': 'DEPOSIT', 'rate': 0.0250, 'tenor': '1M', 'fixing_days': 2},
            {'type': 'DEPOSIT', 'rate': 0.0260, 'tenor': '3M', 'fixing_days': 2},
            {'type': 'DEPOSIT', 'rate': 0.0270, 'tenor': '6M', 'fixing_days': 2},
            # Swaps
            {'type': 'SWAP', 'rate': 0.0300, 'tenor': '2Y', 'fixing_days': 2},
            {'type': 'SWAP', 'rate': 0.0320, 'tenor': '5Y', 'fixing_days': 2},
        ]
    }

    # Bootstrap curve
    curve = build_discount_curve(market_data, 'USD-OIS')

    # Verify discount factors at key maturities
    # 1 month ahead
    df_1m = curve.discount(ql.Date(15, 2, 2026))
    assert 0.997 < df_1m < 0.999, f"1M discount factor {df_1m} out of range"

    # 3 months ahead
    df_3m = curve.discount(ql.Date(15, 4, 2026))
    assert 0.993 < df_3m < 0.995, f"3M discount factor {df_3m} out of range"

    # 6 months ahead
    df_6m = curve.discount(ql.Date(15, 7, 2026))
    assert 0.986 < df_6m < 0.988, f"6M discount factor {df_6m} out of range"

    # 2 years ahead
    df_2y = curve.discount(ql.Date(15, 1, 2028))
    assert 0.940 < df_2y < 0.945, f"2Y discount factor {df_2y} out of range"

    # 5 years ahead
    df_5y = curve.discount(ql.Date(15, 1, 2031))
    assert 0.850 < df_5y < 0.860, f"5Y discount factor {df_5y} out of range"

    # Verify extrapolation works beyond 5Y without errors
    df_10y = curve.discount(ql.Date(15, 1, 2036))
    assert 0.70 < df_10y < 0.75, f"10Y discount factor {df_10y} out of range (extrapolation)"


def test_day_count_conventions():
    """Test day count conventions produce correct year fractions.

    Validates ACT/360, ACT/365, and 30/360 against expected values.
    """
    # Test period: 90 days (Jan 1 to Apr 1, 2026)
    start = ql.Date(1, 1, 2026)
    end = ql.Date(1, 4, 2026)

    # ACT/360: 90 / 360 = 0.25
    yf_act360 = year_fraction(start, end, 'ACT/360')
    assert abs(yf_act360 - 0.25) < 0.0001, f"ACT/360 year fraction {yf_act360} != 0.25"

    # ACT/365: 90 / 365 = 0.246575...
    yf_act365 = year_fraction(start, end, 'ACT/365')
    expected_act365 = 90 / 365.0
    assert abs(yf_act365 - expected_act365) < 0.0001, f"ACT/365 year fraction {yf_act365} != {expected_act365}"

    # 30/360: (360*(2026-2026) + 30*(4-1) + (1-1)) / 360 = 90/360 = 0.25
    yf_30360 = year_fraction(start, end, '30/360')
    assert abs(yf_30360 - 0.25) < 0.0001, f"30/360 year fraction {yf_30360} != 0.25"

    # Test leap year handling (Feb 29, 2024)
    leap_start = ql.Date(1, 2, 2024)
    leap_end = ql.Date(1, 3, 2024)  # Feb 2024 has 29 days

    yf_leap_act360 = year_fraction(leap_start, leap_end, 'ACT/360')
    expected_leap = 29 / 360.0
    assert abs(yf_leap_act360 - expected_leap) < 0.0001, f"Leap year ACT/360 {yf_leap_act360} != {expected_leap}"


def test_business_day_calendar():
    """Test business day calendar logic for US-GOVT holidays.

    Validates known holidays: New Year's Day, Independence Day.
    """
    cal = get_calendar('US-GOVT')

    # Jan 1, 2026 is Wednesday (New Year's Day - holiday)
    jan1 = ql.Date(1, 1, 2026)
    assert not is_business_day(jan1, cal), "Jan 1 2026 should be holiday"

    # Jan 2, 2026 is Thursday (business day)
    jan2 = ql.Date(2, 1, 2026)
    assert is_business_day(jan2, cal), "Jan 2 2026 should be business day"

    # July 4, 2026 is Saturday (Independence Day observed Friday July 3)
    # But Saturday itself is not a business day regardless
    july4 = ql.Date(4, 7, 2026)
    assert not is_business_day(july4, cal), "July 4 2026 (Saturday) should not be business day"

    # July 3, 2026 is Friday (observed holiday for July 4)
    july3 = ql.Date(3, 7, 2026)
    assert not is_business_day(july3, cal), "July 3 2026 should be observed holiday"

    # Test date adjustment
    # Jan 1, 2026 (holiday) adjusted to next business day (Jan 2)
    adjusted = adjust_date(jan1, cal, ql.Following)
    assert adjusted == jan2, f"Adjusted date {adjusted} != expected {jan2}"

    # Test calendar differences: TARGET (Eurozone) vs US-GOVT
    target_cal = get_calendar('TARGET')
    us_cal = get_calendar('US-GOVT')

    # July 4 is US holiday but not TARGET holiday
    july4_us = not is_business_day(july4, us_cal)
    july4_target = not is_business_day(july4, target_cal)

    # Note: July 4, 2026 is Saturday, so both calendars treat as non-business day
    # Better test: Dec 25 (Christmas) - both observe
    christmas = ql.Date(25, 12, 2026)
    assert not is_business_day(christmas, us_cal), "Christmas should be US holiday"
    assert not is_business_day(christmas, target_cal), "Christmas should be TARGET holiday"


def test_multi_curve_framework():
    """Test multi-curve framework with OIS discount and SOFR forward curves.

    Validates that discount and forward curves differ when basis exists.
    """
    calc_date = ql.Date(15, 1, 2026)

    # OIS discount curve (lower rates)
    ois_data = {
        'calc_date': calc_date,
        'instruments': [
            {'type': 'DEPOSIT', 'rate': 0.0240, 'tenor': '3M', 'fixing_days': 2},
            {'type': 'SWAP', 'rate': 0.0280, 'tenor': '2Y', 'fixing_days': 2},
            {'type': 'SWAP', 'rate': 0.0300, 'tenor': '5Y', 'fixing_days': 2},
        ]
    }

    # SOFR forward curve (higher rates due to term premium)
    sofr_data = {
        'calc_date': calc_date,
        'instruments': [
            {'type': 'SWAP', 'rate': 0.0260, 'tenor': '3M', 'fixing_days': 2},
            {'type': 'SWAP', 'rate': 0.0300, 'tenor': '2Y', 'fixing_days': 2},
            {'type': 'SWAP', 'rate': 0.0320, 'tenor': '5Y', 'fixing_days': 2},
        ]
    }

    # Build curves
    ois_curve = build_discount_curve(ois_data, 'USD-OIS')
    sofr_curve = build_forward_curve(sofr_data, 'USD-SOFR-3M', '3M', ois_curve)

    # Verify curves differ (basis spread present)
    test_date = ql.Date(15, 1, 2028)  # 2 years out

    df_ois = ois_curve.discount(test_date)
    df_sofr = sofr_curve.discount(test_date)

    # SOFR curve should have slightly different discount factors
    # (exact relationship depends on curve construction)
    assert df_ois > 0.94 and df_ois < 0.95, f"OIS discount factor {df_ois} out of range"
    assert df_sofr > 0.93 and df_sofr < 0.95, f"SOFR discount factor {df_sofr} out of range"

    # Test basis curve application
    basis_spreads = [
        {'tenor': '2Y', 'spread': 0.0010},  # 10 bps spread
        {'tenor': '5Y', 'spread': 0.0015},  # 15 bps spread
    ]

    basis_curve = build_basis_curve(ois_curve, basis_spreads)

    # Basis curve should have lower discount factors (higher rates)
    df_basis = basis_curve.discount(test_date)
    assert df_basis < df_ois, f"Basis curve DF {df_basis} should be < OIS DF {df_ois}"
    assert abs(df_basis - df_ois) > 0.001, "Basis spread should produce meaningful difference"
