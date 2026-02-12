"""Tests for CECL (Current Expected Credit Loss) calculation.

Golden tests with known scenarios for ASC 326 multi-scenario allowance.
"""
import pytest
from compute.regulatory.cecl import (
    compute_cecl_allowance,
    stage_classification,
    _compute_lifetime_pd,
)


def test_cecl_allowance_single_scenario():
    """CECL allowance with single base scenario."""
    portfolio = [
        {
            "position_id": "pos-1",
            "instrument_id": "loan-1",
            "ead": 1000000,
            "rating": "BBB",
            "base_ccy": "USD",
            "issuer_id": "issuer-abc",
        }
    ]
    pd_curves = {
        "BBB": [0.01, 0.015, 0.02, 0.025, 0.03]  # 5-year PD curve
    }
    lgd_assumptions = {"default": 0.45}
    macro_scenarios = [{"base_rate": 2.5, "unemployment": 4.2}]
    scenario_weights = [1.0]

    result = compute_cecl_allowance(
        portfolio, pd_curves, lgd_assumptions, macro_scenarios, scenario_weights
    )

    # Expected calculation:
    # Lifetime PD = 1 - (0.99 × 0.985 × 0.98 × 0.975 × 0.97) ≈ 0.096
    # ECL = 1,000,000 × 0.096 × 0.45 ≈ 43,200
    assert result["total_allowance"] > 40000
    assert result["total_allowance"] < 50000
    assert "issuer-abc" in result["by_segment"]
    assert len(result["scenario_detail"]) == 1


def test_cecl_allowance_multi_scenario():
    """CECL allowance with multiple weighted scenarios."""
    portfolio = [
        {
            "position_id": "pos-1",
            "instrument_id": "loan-1",
            "ead": 2000000,
            "rating": "A",
            "base_ccy": "USD",
            "issuer_id": "corp-xyz",
        }
    ]
    pd_curves = {
        "A": [0.005, 0.008, 0.010, 0.012, 0.015]
    }
    lgd_assumptions = {"default": 0.40}
    # Three scenarios: base, adverse, severely adverse
    macro_scenarios = [
        {"name": "base"},
        {"name": "adverse"},
        {"name": "severely_adverse"},
    ]
    scenario_weights = [0.60, 0.30, 0.10]

    result = compute_cecl_allowance(
        portfolio, pd_curves, lgd_assumptions, macro_scenarios, scenario_weights
    )

    # All scenarios use same PD curve in this implementation
    # Lifetime PD ≈ 1 - (0.995 × 0.992 × 0.990 × 0.988 × 0.985) ≈ 0.050
    # ECL = 2,000,000 × 0.050 × 0.40 = 40,000
    # Weighted: same across scenarios, so 40,000
    assert result["total_allowance"] > 35000
    assert result["total_allowance"] < 45000
    assert len(result["scenario_detail"]) == 3


def test_cecl_allowance_multiple_segments():
    """CECL allowance with multiple issuers (segments)."""
    portfolio = [
        {
            "position_id": "pos-1",
            "instrument_id": "loan-1",
            "ead": 1000000,
            "rating": "BBB",
            "issuer_id": "issuer-1",
        },
        {
            "position_id": "pos-2",
            "instrument_id": "loan-2",
            "ead": 500000,
            "rating": "BBB",
            "issuer_id": "issuer-1",
        },
        {
            "position_id": "pos-3",
            "instrument_id": "loan-3",
            "ead": 2000000,
            "rating": "BB",
            "issuer_id": "issuer-2",
        },
    ]
    pd_curves = {
        "BBB": [0.02, 0.025, 0.03],
        "BB": [0.05, 0.06, 0.07],
    }
    lgd_assumptions = {"default": 0.45}
    macro_scenarios = [{"base": True}]
    scenario_weights = [1.0]

    result = compute_cecl_allowance(
        portfolio, pd_curves, lgd_assumptions, macro_scenarios, scenario_weights
    )

    # Two segments: issuer-1 (1.5M EAD, BBB) and issuer-2 (2M EAD, BB)
    assert "issuer-1" in result["by_segment"]
    assert "issuer-2" in result["by_segment"]
    # Issuer-2 (BB) should have higher allowance due to higher PD
    assert result["by_segment"]["issuer-2"] > result["by_segment"]["issuer-1"]
    assert result["total_allowance"] > 0


def test_cecl_allowance_with_q_factor():
    """CECL allowance with qualitative adjustment (Q-factor)."""
    portfolio = [
        {
            "position_id": "pos-1",
            "instrument_id": "loan-1",
            "ead": 1000000,
            "rating": "A",
            "issuer_id": "issuer-1",
        }
    ]
    pd_curves = {"A": [0.005, 0.008, 0.010]}
    lgd_assumptions = {"default": 0.45}
    macro_scenarios = [{"base": True}]
    scenario_weights = [1.0]

    # Without Q-factor
    result_no_q = compute_cecl_allowance(
        portfolio, pd_curves, lgd_assumptions, macro_scenarios, scenario_weights
    )

    # With 10% Q-factor
    result_with_q = compute_cecl_allowance(
        portfolio,
        pd_curves,
        lgd_assumptions,
        macro_scenarios,
        scenario_weights,
        q_factor=0.10,
    )

    # With Q-factor should be 10% higher
    assert abs(result_with_q["total_allowance"] - result_no_q["total_allowance"] * 1.10) < 1.0


def test_cecl_allowance_fallback_pd_curve():
    """CECL allowance with missing PD curve (fallback to default)."""
    portfolio = [
        {
            "position_id": "pos-1",
            "instrument_id": "loan-1",
            "ead": 1000000,
            "rating": "NR",  # Not rated - not in pd_curves
            "issuer_id": "issuer-1",
        }
    ]
    pd_curves = {}  # Empty - will use fallback
    lgd_assumptions = {"default": 0.45}
    macro_scenarios = [{"base": True}]
    scenario_weights = [1.0]

    result = compute_cecl_allowance(
        portfolio, pd_curves, lgd_assumptions, macro_scenarios, scenario_weights
    )

    # Should still produce a result using fallback (flat 2% PD)
    assert result["total_allowance"] > 0


def test_cecl_empty_portfolio():
    """CECL allowance with empty portfolio."""
    result = compute_cecl_allowance([], {}, {}, [], [])

    assert result["total_allowance"] == 0.0
    assert result["by_segment"] == {}
    assert result["scenario_detail"] == []


def test_compute_lifetime_pd():
    """Lifetime PD calculation from marginal annual PD curve."""
    # Test case from plan example
    pd_curve = [0.01, 0.015, 0.02]
    lifetime_pd = _compute_lifetime_pd(pd_curve)

    # Expected: 1 - (0.99 × 0.985 × 0.98) ≈ 0.0446
    assert abs(lifetime_pd - 0.0446) < 0.001


def test_compute_lifetime_pd_high_pd():
    """Lifetime PD with high default probabilities."""
    pd_curve = [0.20, 0.25, 0.30]
    lifetime_pd = _compute_lifetime_pd(pd_curve)

    # High cumulative PD
    # 1 - (0.80 × 0.75 × 0.70) = 1 - 0.42 = 0.58
    assert abs(lifetime_pd - 0.58) < 0.01


def test_compute_lifetime_pd_cap():
    """Lifetime PD capped at 99.9%."""
    pd_curve = [0.99, 0.99, 0.99]
    lifetime_pd = _compute_lifetime_pd(pd_curve)

    # Should cap at 0.999
    assert lifetime_pd == 0.999


def test_compute_lifetime_pd_empty():
    """Lifetime PD with empty curve."""
    lifetime_pd = _compute_lifetime_pd([])
    assert lifetime_pd == 0.0


def test_stage_classification():
    """IFRS 9 / CECL stage classification."""
    # Stage 1: No deterioration
    assert stage_classification(0.02, 0.01, 0) == 1

    # Stage 2: PD doubled (significant deterioration)
    assert stage_classification(0.03, 0.01, 0) == 2

    # Stage 3: >90 DPD (credit-impaired)
    assert stage_classification(0.02, 0.01, 100) == 3

    # Stage 3 takes precedence even with low PD
    assert stage_classification(0.01, 0.01, 95) == 3


def test_stage_classification_exact_threshold():
    """Stage classification at exact 2x threshold."""
    # Exactly 2x origination PD
    assert stage_classification(0.02, 0.01, 0) == 1  # Not greater than

    # Slightly over 2x
    assert stage_classification(0.021, 0.01, 0) == 2


def test_stage_classification_dpd_threshold():
    """Stage classification at DPD threshold."""
    # Exactly 90 DPD (not credit-impaired)
    # With PD deterioration to trigger Stage 2
    assert stage_classification(0.03, 0.01, 90) == 2

    # 91 DPD (credit-impaired) - Stage 3 takes precedence
    assert stage_classification(0.02, 0.01, 91) == 3
