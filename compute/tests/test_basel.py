"""Tests for Basel III RWA and capital ratio calculations.

Golden tests with known risk weights per Basel III standardized approach.
"""
import pytest
from compute.regulatory.basel import (
    compute_basel_rwa,
    get_risk_weight,
    compute_capital_ratios,
)


# Basel III Standardized Approach risk weights
# Per Basel Committee on Banking Supervision (BCBS) guidelines
STANDARD_RISK_WEIGHTS = {
    # Sovereigns
    ('SOVEREIGN', 'AAA'): 0.00,
    ('SOVEREIGN', 'AA'): 0.20,
    ('SOVEREIGN', 'A'): 0.50,
    ('SOVEREIGN', 'BBB'): 1.00,
    ('SOVEREIGN', 'BB'): 1.00,
    ('SOVEREIGN', 'B'): 1.50,
    # Corporates
    ('CORPORATE', 'AAA'): 0.20,
    ('CORPORATE', 'AA'): 0.20,
    ('CORPORATE', 'A'): 0.50,
    ('CORPORATE', 'BBB'): 1.00,
    ('CORPORATE', 'BB'): 1.50,
    ('CORPORATE', 'B'): 1.50,
    ('CORPORATE', 'CCC'): 1.50,
    # Retail
    ('RETAIL', 'ANY'): 0.75,
    # Unrated
    ('UNRATED', 'ANY'): 1.00,
}


def test_basel_rwa_corporate_portfolio():
    """Basel III RWA for corporate portfolio with mixed ratings."""
    portfolio = [
        {
            "position_id": "pos-1",
            "ead": 1000000,
            "counterparty_type": "CORPORATE",
            "rating": "AAA",
        },
        {
            "position_id": "pos-2",
            "ead": 2000000,
            "counterparty_type": "CORPORATE",
            "rating": "BBB",
        },
        {
            "position_id": "pos-3",
            "ead": 500000,
            "counterparty_type": "RETAIL",
            "rating": "ANY",
        },
    ]
    risk_weights = {
        ('CORPORATE', 'AAA'): 0.20,
        ('CORPORATE', 'BBB'): 1.00,
        ('RETAIL', 'ANY'): 0.75,
    }

    result = compute_basel_rwa(portfolio, risk_weights)

    # Expected RWA:
    # pos-1: 1M × 0.20 = 200K
    # pos-2: 2M × 1.00 = 2M
    # pos-3: 0.5M × 0.75 = 375K
    # Total: 2,575,000
    assert abs(result["total_rwa"] - 2575000) < 1000
    assert result["by_counterparty_type"]["CORPORATE"] > 2000000
    assert result["by_rating"]["BBB"] == 2000000
    assert len(result["detail"]) == 3


def test_basel_rwa_sovereign_exposures():
    """Basel III RWA for sovereign exposures with low risk weights."""
    portfolio = [
        {
            "position_id": "us-treasury",
            "ead": 10000000,
            "counterparty_type": "SOVEREIGN",
            "rating": "AAA",
        },
        {
            "position_id": "eu-bond",
            "ead": 5000000,
            "counterparty_type": "SOVEREIGN",
            "rating": "AA",
        },
    ]

    result = compute_basel_rwa(portfolio, STANDARD_RISK_WEIGHTS)

    # Expected RWA:
    # US Treasury: 10M × 0.00 = 0 (zero risk weight for AAA sovereign)
    # EU Bond: 5M × 0.20 = 1M
    # Total: 1,000,000
    assert abs(result["total_rwa"] - 1000000) < 1000
    assert result["by_counterparty_type"]["SOVEREIGN"] == 1000000


def test_basel_rwa_mixed_portfolio():
    """Basel III RWA for mixed portfolio (sovereign, corporate, retail)."""
    portfolio = [
        {"position_id": "p1", "ead": 1000000, "counterparty_type": "SOVEREIGN", "rating": "AAA"},
        {"position_id": "p2", "ead": 2000000, "counterparty_type": "CORPORATE", "rating": "A"},
        {"position_id": "p3", "ead": 3000000, "counterparty_type": "CORPORATE", "rating": "BB"},
        {"position_id": "p4", "ead": 1500000, "counterparty_type": "RETAIL", "rating": "ANY"},
    ]

    result = compute_basel_rwa(portfolio, STANDARD_RISK_WEIGHTS)

    # Expected RWA:
    # p1: 1M × 0.00 = 0
    # p2: 2M × 0.50 = 1M
    # p3: 3M × 1.50 = 4.5M
    # p4: 1.5M × 0.75 = 1.125M
    # Total: 6,625,000
    assert abs(result["total_rwa"] - 6625000) < 1000
    assert "SOVEREIGN" in result["by_counterparty_type"]
    assert "CORPORATE" in result["by_counterparty_type"]
    assert "RETAIL" in result["by_counterparty_type"]


def test_basel_rwa_unrated_default():
    """Basel III RWA for unrated exposures (default 100% risk weight)."""
    portfolio = [
        {
            "position_id": "unrated-loan",
            "ead": 1000000,
            "counterparty_type": "UNRATED",
            "rating": "NR",
        }
    ]

    result = compute_basel_rwa(portfolio, STANDARD_RISK_WEIGHTS)

    # Expected RWA: 1M × 1.00 = 1M (100% default risk weight)
    assert abs(result["total_rwa"] - 1000000) < 1000


def test_basel_rwa_empty_portfolio():
    """Basel III RWA for empty portfolio."""
    result = compute_basel_rwa([], STANDARD_RISK_WEIGHTS)

    assert result["total_rwa"] == 0.0
    assert result["by_counterparty_type"] == {}
    assert result["by_rating"] == {}
    assert result["detail"] == []


def test_get_risk_weight_exact_match():
    """Risk weight lookup with exact match."""
    weights = {
        ('CORPORATE', 'AAA'): 0.20,
        ('CORPORATE', 'BBB'): 1.00,
    }

    assert get_risk_weight('CORPORATE', 'AAA', weights) == 0.20
    assert get_risk_weight('CORPORATE', 'BBB', weights) == 1.00


def test_get_risk_weight_fallback_any():
    """Risk weight lookup with ANY fallback."""
    weights = {
        ('RETAIL', 'ANY'): 0.75,
    }

    # Should use ANY fallback for any rating
    assert get_risk_weight('RETAIL', 'A', weights) == 0.75
    assert get_risk_weight('RETAIL', 'BBB', weights) == 0.75
    assert get_risk_weight('RETAIL', 'NR', weights) == 0.75


def test_get_risk_weight_default():
    """Risk weight lookup with default 100% for unknown."""
    weights = {}  # Empty risk weights

    # Should default to 1.00 (100%)
    assert get_risk_weight('CORPORATE', 'AAA', weights) == 1.00
    assert get_risk_weight('UNKNOWN', 'UNKNOWN', weights) == 1.00


def test_compute_capital_ratios():
    """Basel III capital ratios calculation."""
    ratios = compute_capital_ratios(
        total_rwa=10000000,
        tier1_capital=800000,
        tier2_capital=200000,
    )

    # CET1 ratio = 800K / 10M = 8%
    assert abs(ratios["cet1_ratio"] - 0.08) < 0.001

    # Tier 1 ratio = 800K / 10M = 8%
    assert abs(ratios["tier1_ratio"] - 0.08) < 0.001

    # Total capital ratio = (800K + 200K) / 10M = 10%
    assert abs(ratios["total_capital_ratio"] - 0.10) < 0.001


def test_compute_capital_ratios_minimum_requirements():
    """Basel III capital ratios at minimum regulatory thresholds."""
    # Test at minimum CET1 = 4.5%
    ratios_min_cet1 = compute_capital_ratios(
        total_rwa=10000000,
        tier1_capital=450000,  # 4.5%
        tier2_capital=150000,  # Additional 1.5% to reach 6% Tier 1
    )
    assert abs(ratios_min_cet1["cet1_ratio"] - 0.045) < 0.001

    # Test at minimum Total Capital = 8%
    ratios_min_total = compute_capital_ratios(
        total_rwa=10000000,
        tier1_capital=600000,  # 6%
        tier2_capital=200000,  # 2% to reach 8%
    )
    assert abs(ratios_min_total["total_capital_ratio"] - 0.08) < 0.001


def test_compute_capital_ratios_zero_rwa():
    """Capital ratios with zero RWA (no exposures)."""
    ratios = compute_capital_ratios(
        total_rwa=0.0,
        tier1_capital=1000000,
        tier2_capital=500000,
    )

    # All ratios should be 0.0 when RWA is zero
    assert ratios["cet1_ratio"] == 0.0
    assert ratios["tier1_ratio"] == 0.0
    assert ratios["total_capital_ratio"] == 0.0


def test_compute_capital_ratios_well_capitalized():
    """Capital ratios for well-capitalized institution."""
    # Well above minimum requirements
    ratios = compute_capital_ratios(
        total_rwa=10000000,
        tier1_capital=1500000,  # 15% (well above 6% minimum)
        tier2_capital=500000,   # Additional 5%
    )

    assert ratios["cet1_ratio"] >= 0.045  # Above 4.5% minimum
    assert ratios["tier1_ratio"] >= 0.06  # Above 6% minimum
    assert ratios["total_capital_ratio"] >= 0.08  # Above 8% minimum

    # Total capital ratio = 20%
    assert abs(ratios["total_capital_ratio"] - 0.20) < 0.001


def test_basel_rwa_aggregation_by_rating():
    """RWA aggregation by credit rating."""
    portfolio = [
        {"position_id": "p1", "ead": 1000000, "counterparty_type": "CORPORATE", "rating": "AAA"},
        {"position_id": "p2", "ead": 2000000, "counterparty_type": "CORPORATE", "rating": "AAA"},
        {"position_id": "p3", "ead": 1500000, "counterparty_type": "CORPORATE", "rating": "BBB"},
    ]

    result = compute_basel_rwa(portfolio, STANDARD_RISK_WEIGHTS)

    # AAA: (1M + 2M) × 0.20 = 600K
    # BBB: 1.5M × 1.00 = 1.5M
    assert abs(result["by_rating"]["AAA"] - 600000) < 1000
    assert abs(result["by_rating"]["BBB"] - 1500000) < 1000


def test_basel_rwa_detail_output():
    """RWA calculation includes position-level detail."""
    portfolio = [
        {"position_id": "loan-1", "ead": 1000000, "counterparty_type": "CORPORATE", "rating": "A"},
    ]

    result = compute_basel_rwa(portfolio, STANDARD_RISK_WEIGHTS)

    assert len(result["detail"]) == 1
    detail = result["detail"][0]
    assert detail["position_id"] == "loan-1"
    assert detail["ead"] == 1000000
    assert detail["counterparty_type"] == "CORPORATE"
    assert detail["rating"] == "A"
    assert detail["risk_weight"] == 0.50
    assert detail["rwa"] == 500000
