"""Comprehensive tests for market risk analytics."""
import pytest
from compute.risk.market.duration import (
    macaulay_duration,
    modified_duration,
    effective_duration,
    calculate_all_durations,
)
from compute.risk.market.dv01 import calculate_dv01, calculate_pv01
from compute.risk.market.convexity import calculate_convexity
from compute.risk.market.spread_duration import calculate_spread_duration
from compute.risk.market.key_rate import calculate_key_rate_durations


@pytest.fixture
def sample_bond_cashflows():
    """5-year 5% semi-annual bond cashflows."""
    cashflows = []
    for i in range(1, 11):  # 10 semi-annual periods
        year_fraction = i * 0.5
        payment = 2.5 if i < 10 else 102.5  # 2.5% coupon, 100 principal at maturity
        cashflows.append({
            'year_fraction': year_fraction,
            'payment': payment,
        })
    return cashflows


@pytest.fixture
def short_bond_cashflows():
    """3-period bond for duration tests."""
    return [
        {'year_fraction': 0.5, 'payment': 2.5},
        {'year_fraction': 1.0, 'payment': 2.5},
        {'year_fraction': 1.5, 'payment': 102.5},
    ]


def test_macaulay_duration(sample_bond_cashflows):
    """Test Macaulay duration for 5-year bond."""
    ytm = 0.05  # 5% YTM
    mac_dur = macaulay_duration(sample_bond_cashflows, ytm, frequency=2)

    # For a 5-year bond, Macaulay duration should be between 4 and 5 years
    assert 4.0 < mac_dur < 5.0, f"Macaulay duration {mac_dur} outside expected range"

    # More precise check: 5-year bond at par should have duration ~4.3 years
    assert 4.2 < mac_dur < 4.5, f"Macaulay duration {mac_dur} not close to expected ~4.3"


def test_macaulay_duration_short_bond(short_bond_cashflows):
    """Test Macaulay duration calculation accuracy."""
    ytm = 0.05
    mac_dur = macaulay_duration(short_bond_cashflows, ytm, frequency=2)

    # 3-period bond should have duration between 1.3 and 1.5 years
    assert 1.3 < mac_dur < 1.5, f"Macaulay duration {mac_dur} outside expected range"


def test_modified_duration(sample_bond_cashflows):
    """Test Modified duration derivation."""
    ytm = 0.05
    frequency = 2

    mac_dur = macaulay_duration(sample_bond_cashflows, ytm, frequency)
    mod_dur = modified_duration(mac_dur, ytm, frequency)

    # Modified duration should always be less than Macaulay
    assert mod_dur < mac_dur, "Modified duration should be less than Macaulay"

    # Check formula: ModD = MacD / (1 + ytm/freq)
    expected_mod = mac_dur / (1.0 + ytm / frequency)
    assert abs(mod_dur - expected_mod) < 0.0001, "Modified duration formula incorrect"


def test_effective_duration_positive_convexity():
    """Test effective duration for typical bond with positive convexity."""
    pv_base = 100.0
    pv_down = 102.5  # rates down 50bp -> price up 2.5
    pv_up = 97.6     # rates up 50bp -> price down 2.4 (less due to convexity)
    shock_bps = 50.0

    eff_dur = effective_duration(pv_down, pv_up, pv_base, shock_bps)

    # Effective duration should be positive
    assert eff_dur > 0, "Effective duration should be positive"

    # For a typical bond, duration should be in reasonable range
    assert 1.0 < eff_dur < 20.0, f"Effective duration {eff_dur} outside typical range"

    # For this example: (102.5 - 97.6) / (2 * 100.0 * 0.005) = 4.9
    expected = (pv_down - pv_up) / (2.0 * pv_base * shock_bps / 10000.0)
    assert abs(eff_dur - expected) < 0.01, "Effective duration formula incorrect"


def test_dv01_calculation():
    """Test DV01 for $1M bond with 5% duration."""
    # For a $1M bond with duration 5, 1bp increase should cause ~$500 loss
    notional = 1_000_000.0
    duration_years = 5.0

    # Approximate PV change: -Duration * PV * yield_change
    # For 1bp = 0.0001: PV_change ≈ -5 * 1M * 0.0001 = -500
    price_base = notional
    price_up_1bp = notional - (duration_years * notional * 0.0001)

    dv01 = calculate_dv01(price_base, price_up_1bp)

    # DV01 should be approximately $500
    assert 400 < dv01 < 600, f"DV01 {dv01} outside expected range"

    # Should be positive (loss when rates rise)
    assert dv01 > 0, "DV01 should be positive"


def test_dv01_zero_base_price():
    """Test DV01 validation for zero base price."""
    with pytest.raises(ValueError, match="Base price cannot be zero"):
        calculate_dv01(0.0, 99.95)


def test_convexity_positive():
    """Test convexity for typical bond."""
    pv_base = 100.0
    pv_down = 102.5  # rates down 50bp
    pv_up = 97.6     # rates up 50bp
    shock_bps = 50.0

    conv = calculate_convexity(pv_base, pv_down, pv_up, shock_bps)

    # Typical bonds have positive convexity
    assert conv > 0, f"Convexity {conv} should be positive for typical bond"

    # Verify formula: (PV_up + PV_down - 2*PV_base) / (PV_base * shock^2)
    shock = shock_bps / 10000.0
    expected = (pv_down + pv_up - 2.0 * pv_base) / (pv_base * shock * shock)
    assert abs(conv - expected) < 0.01, "Convexity formula incorrect"

    # Verify PV_down + PV_up > 2 * PV_base (definition of positive convexity)
    assert pv_down + pv_up > 2.0 * pv_base, "Positive convexity condition violated"


def test_convexity_validation():
    """Test convexity input validation."""
    with pytest.raises(ValueError, match="Base PV must be positive"):
        calculate_convexity(0.0, 102.5, 97.6, 50.0)

    with pytest.raises(ValueError, match="Shock must be positive"):
        calculate_convexity(100.0, 102.5, 97.6, -10.0)


def test_spread_duration():
    """Test spread duration for corporate bond."""
    pv_base = 100.0
    pv_spread_up = 98.75  # 25bp spread widening -> price down 1.25
    spread_shock_bps = 25.0

    spread_dur = calculate_spread_duration(pv_base, pv_spread_up, spread_shock_bps)

    # Spread duration should be positive
    assert spread_dur > 0, "Spread duration should be positive"

    # For this example: (100.0 - 98.75) / (100.0 * 0.0025) = 5.0
    expected = (pv_base - pv_spread_up) / (pv_base * spread_shock_bps / 10000.0)
    assert abs(spread_dur - expected) < 0.01, "Spread duration formula incorrect"


def test_spread_duration_validation():
    """Test spread duration input validation."""
    with pytest.raises(ValueError, match="Base PV must be positive"):
        calculate_spread_duration(0.0, 98.75, 25.0)

    with pytest.raises(ValueError, match="Spread shock must be positive"):
        calculate_spread_duration(100.0, 98.75, 0.0)


def test_key_rate_durations_sum():
    """Test that sum of key rate durations approximates effective duration."""
    # Base case
    pv_base = 100.0
    shock_bps = 10.0

    # Shocked PVs for 3 tenors
    shocked_pvs = {
        '2Y': 99.5,   # 2Y rate up 10bp -> duration contribution 5.0
        '5Y': 99.3,   # 5Y rate up 10bp -> duration contribution 7.0
        '10Y': 99.0,  # 10Y rate up 10bp -> duration contribution 10.0
    }

    krd = calculate_key_rate_durations(pv_base, shocked_pvs, shock_bps)

    # Verify individual KRDs are positive
    for tenor, dur in krd.items():
        assert dur > 0, f"Key rate duration for {tenor} should be positive"

    # Sum of KRDs
    total_krd = sum(krd.values())

    # For this example, total should be around 22.0
    assert 20.0 < total_krd < 24.0, f"Sum of KRDs {total_krd} outside expected range"

    # Calculate effective duration from full parallel shift
    # If we shifted all rates, total impact would be sum of individual impacts
    pv_all_up = pv_base - sum(pv_base - pv for pv in shocked_pvs.values())
    eff_dur = (pv_base - pv_all_up) / (pv_base * shock_bps / 10000.0)

    # Sum of KRDs should approximately equal effective duration
    # Allow 15% tolerance (conservative for 3-point approximation)
    tolerance = 0.15
    ratio = abs(total_krd - eff_dur) / max(eff_dur, 1e-6)
    assert ratio < tolerance, (
        f"Sum of KRDs ({total_krd:.4f}) too far from "
        f"effective duration ({eff_dur:.4f}), ratio: {ratio:.2%}"
    )


def test_key_rate_durations_callable_bond():
    """Test that callable bonds can have negative key rate durations."""
    # Callable bonds can have negative duration in call-sensitive tenors
    # When rates fall, call becomes more likely, limiting price appreciation
    pv_base = 100.0
    shock_bps = 10.0

    # Simulate callable bond: short-end rate increase reduces call risk, increases value
    shocked_pvs = {
        '2Y': 100.2,   # Short rate up -> less likely to call -> price up (negative duration)
        '5Y': 99.7,    # Medium rate up -> normal behavior (positive duration)
        '10Y': 99.5,   # Long rate up -> normal behavior (positive duration)
    }

    krd = calculate_key_rate_durations(pv_base, shocked_pvs, shock_bps)

    # 2Y should have negative duration (price up when rates rise)
    assert krd['2Y'] < 0, "Callable bond can have negative KRD in call-sensitive tenor"

    # Longer tenors should have positive duration
    assert krd['5Y'] > 0, "5Y KRD should be positive"
    assert krd['10Y'] > 0, "10Y KRD should be positive"


def test_calculate_all_durations(sample_bond_cashflows):
    """Test convenience function for calculating all duration types."""
    ytm = 0.05
    pv_base = 100.0
    pv_down = 102.5
    pv_up = 97.6

    all_durs = calculate_all_durations(
        sample_bond_cashflows,
        ytm,
        pv_base,
        pv_down,
        pv_up,
        frequency=2,
        shock_bps=50.0,
    )

    # Should return dict with three keys
    assert 'macaulay' in all_durs, "Missing Macaulay duration"
    assert 'modified' in all_durs, "Missing Modified duration"
    assert 'effective' in all_durs, "Missing Effective duration"

    # All should be positive
    assert all_durs['macaulay'] > 0, "Macaulay duration should be positive"
    assert all_durs['modified'] > 0, "Modified duration should be positive"
    assert all_durs['effective'] > 0, "Effective duration should be positive"

    # Modified < Macaulay (always true)
    assert all_durs['modified'] < all_durs['macaulay'], (
        "Modified duration should be less than Macaulay"
    )

    # Effective should be close to Modified for small shocks
    ratio = abs(all_durs['effective'] - all_durs['modified']) / all_durs['modified']
    assert ratio < 0.2, (
        f"Effective ({all_durs['effective']:.4f}) too far from "
        f"Modified ({all_durs['modified']:.4f})"
    )


def test_pv01_from_cashflows(short_bond_cashflows):
    """Test PV01 calculation from cashflows."""
    ytm = 0.05
    frequency = 2

    pv01 = calculate_pv01(short_bond_cashflows, ytm, frequency)

    # PV01 should be positive
    assert pv01 > 0, "PV01 should be positive"

    # For a 1.5-year bond at par (≈100), PV01 should be around 0.014
    # (duration ~1.46, PV01 ≈ 1.46 * 100 / 10000 ≈ 0.0146)
    assert 0.01 < pv01 < 0.02, f"PV01 {pv01} outside expected range"
