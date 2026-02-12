"""Tests for GAAP/IFRS valuation framework.

Golden tests for classification and valuation under US GAAP (ASC 320)
and IFRS 9 standards.
"""
import pytest
from compute.regulatory.gaap_ifrs import (
    classify_gaap_category,
    classify_ifrs_category,
    compute_impairment,
    compute_gaap_valuation,
    compute_ifrs_valuation,
)


def test_gaap_classification():
    """GAAP category classification by management intent."""
    # Held-to-Maturity
    assert classify_gaap_category({"intent": "HTM"}) == "HELD_TO_MATURITY"

    # Available-for-Sale
    assert classify_gaap_category({"intent": "AFS"}) == "AVAILABLE_FOR_SALE"

    # Trading
    assert classify_gaap_category({"intent": "TRADING"}) == "TRADING"

    # Default (no intent specified)
    assert classify_gaap_category({}) == "AVAILABLE_FOR_SALE"


def test_gaap_classification_case_insensitive():
    """GAAP classification is case-insensitive."""
    assert classify_gaap_category({"intent": "htm"}) == "HELD_TO_MATURITY"
    assert classify_gaap_category({"intent": "Afs"}) == "AVAILABLE_FOR_SALE"
    assert classify_gaap_category({"intent": "trading"}) == "TRADING"


def test_ifrs_classification_amortized_cost():
    """IFRS 9 classification: Amortized Cost."""
    position = {
        "business_model": "HOLD_TO_COLLECT",
        "product_type": "FIXED_BOND",
    }

    assert classify_ifrs_category(position) == "AMORTIZED_COST"


def test_ifrs_classification_fvoci():
    """IFRS 9 classification: Fair Value through OCI."""
    position = {
        "business_model": "HOLD_AND_SELL",
        "product_type": "AMORT_LOAN",
    }

    assert classify_ifrs_category(position) == "FVOCI"


def test_ifrs_classification_fvtpl():
    """IFRS 9 classification: Fair Value through P&L."""
    # Derivative (fails SPPI test)
    position_derivative = {
        "business_model": "HOLD_TO_COLLECT",
        "product_type": "FX_FWD",
    }
    assert classify_ifrs_category(position_derivative) == "FVTPL"

    # Trading business model
    position_trading = {
        "business_model": "TRADING",
        "product_type": "FIXED_BOND",
    }
    assert classify_ifrs_category(position_trading) == "FVTPL"


def test_ifrs_classification_sppi_pass():
    """IFRS 9 SPPI test passes for bonds and loans."""
    sppi_instruments = [
        "FIXED_BOND",
        "AMORT_LOAN",
        "FLOATING_RATE_NOTE",
        "CALLABLE_BOND",
        "PUTABLE_BOND",
    ]

    for product_type in sppi_instruments:
        position = {
            "business_model": "HOLD_TO_COLLECT",
            "product_type": product_type,
        }
        # Should classify as Amortized Cost (SPPI + hold-to-collect)
        assert classify_ifrs_category(position) == "AMORTIZED_COST"


def test_ifrs_classification_override_business_model():
    """IFRS classification with business model override parameter."""
    position = {"product_type": "FIXED_BOND"}

    # Override with parameter
    assert classify_ifrs_category(position, business_model="HOLD_TO_COLLECT") == "AMORTIZED_COST"
    assert classify_ifrs_category(position, business_model="HOLD_AND_SELL") == "FVOCI"
    assert classify_ifrs_category(position, business_model="TRADING") == "FVTPL"


def test_compute_impairment_htm_no_impairment():
    """GAAP impairment: HTM with no impairment (< 10% decline)."""
    position = {"intent": "HTM"}

    # Market value 95% of book (5% decline - below 10% threshold)
    impairment = compute_impairment(
        position,
        market_value=950000,
        book_value=1000000,
        category="HELD_TO_MATURITY",
    )

    assert impairment == 0.0


def test_compute_impairment_htm_with_impairment():
    """GAAP impairment: HTM with impairment (> 10% decline)."""
    position = {"intent": "HTM"}

    # Market value 85% of book (15% decline - above 10% threshold)
    impairment = compute_impairment(
        position,
        market_value=850000,
        book_value=1000000,
        category="HELD_TO_MATURITY",
    )

    # Impairment = book - market = 150,000
    assert impairment == 150000


def test_compute_impairment_afs_no_impairment():
    """GAAP impairment: AFS has no impairment to book value."""
    position = {"intent": "AFS"}

    # Even with large decline, AFS doesn't impair book value
    impairment = compute_impairment(
        position,
        market_value=500000,
        book_value=1000000,
        category="AVAILABLE_FOR_SALE",
    )

    assert impairment == 0.0


def test_gaap_htm_valuation_no_impairment():
    """GAAP HTM valuation without impairment."""
    position = {"intent": "HTM", "product_type": "FIXED_BOND"}

    result = compute_gaap_valuation(
        position,
        market_value=980000,  # 2% decline
        book_value=1000000,
    )

    assert result["category"] == "HELD_TO_MATURITY"
    assert result["carrying_value"] == 1000000  # Book value (no impairment)
    assert result["impairment"] == 0.0
    assert result["unrealized_gain_loss"] == 0.0


def test_gaap_htm_valuation_with_impairment():
    """GAAP HTM valuation with impairment."""
    position = {"intent": "HTM", "product_type": "FIXED_BOND"}

    result = compute_gaap_valuation(
        position,
        market_value=850000,  # 15% decline
        book_value=1000000,
    )

    assert result["category"] == "HELD_TO_MATURITY"
    assert result["carrying_value"] == 850000  # Book - impairment
    assert result["impairment"] == 150000
    assert result["unrealized_gain_loss"] == 0.0


def test_gaap_afs_valuation():
    """GAAP AFS valuation at fair value."""
    position = {"intent": "AFS", "product_type": "FIXED_BOND"}

    result = compute_gaap_valuation(
        position,
        market_value=1050000,
        book_value=1000000,
    )

    assert result["category"] == "AVAILABLE_FOR_SALE"
    assert result["carrying_value"] == 1050000  # Market value
    assert result["unrealized_gain_loss"] == 50000  # In OCI
    assert result["impairment"] == 0.0


def test_gaap_afs_valuation_unrealized_loss():
    """GAAP AFS valuation with unrealized loss in OCI."""
    position = {"intent": "AFS"}

    result = compute_gaap_valuation(
        position,
        market_value=900000,
        book_value=1000000,
    )

    assert result["category"] == "AVAILABLE_FOR_SALE"
    assert result["carrying_value"] == 900000
    assert result["unrealized_gain_loss"] == -100000  # Loss in OCI
    assert result["impairment"] == 0.0


def test_gaap_trading_valuation():
    """GAAP Trading valuation at fair value through P&L."""
    position = {"intent": "TRADING"}

    result = compute_gaap_valuation(
        position,
        market_value=1080000,
        book_value=1000000,
    )

    assert result["category"] == "TRADING"
    assert result["carrying_value"] == 1080000  # Market value
    assert result["realized_gain_loss"] == 80000  # In P&L
    assert result["unrealized_gain_loss"] == 0.0


def test_ifrs_amortized_cost_with_ecl():
    """IFRS amortized cost valuation with ECL allowance."""
    position = {
        "business_model": "HOLD_TO_COLLECT",
        "product_type": "AMORT_LOAN",
    }

    result = compute_ifrs_valuation(
        position,
        market_value=980000,
        book_value=1000000,
        ecl_allowance=50000,
    )

    assert result["category"] == "AMORTIZED_COST"
    assert result["carrying_value"] == 950000  # Book - ECL
    assert result["ecl_allowance"] == 50000
    assert result["unrealized_gain_loss"] == 0.0


def test_ifrs_amortized_cost_zero_ecl():
    """IFRS amortized cost valuation with zero ECL."""
    position = {
        "business_model": "HOLD_TO_COLLECT",
        "product_type": "FIXED_BOND",
    }

    result = compute_ifrs_valuation(
        position,
        market_value=1020000,
        book_value=1000000,
        ecl_allowance=0.0,
    )

    assert result["category"] == "AMORTIZED_COST"
    assert result["carrying_value"] == 1000000  # Book value
    assert result["ecl_allowance"] == 0.0


def test_ifrs_fvoci_valuation():
    """IFRS FVOCI valuation with unrealized gain in OCI."""
    position = {
        "business_model": "HOLD_AND_SELL",
        "product_type": "FIXED_BOND",
    }

    result = compute_ifrs_valuation(
        position,
        market_value=1100000,
        book_value=1000000,
    )

    assert result["category"] == "FVOCI"
    assert result["carrying_value"] == 1100000  # Fair value
    assert result["unrealized_gain_loss"] == 100000  # In OCI
    assert result["ecl_allowance"] == 0.0


def test_ifrs_fvtpl_valuation():
    """IFRS FVTPL valuation through P&L."""
    position = {
        "business_model": "TRADING",
        "product_type": "FIXED_BOND",
    }

    result = compute_ifrs_valuation(
        position,
        market_value=1150000,
        book_value=1000000,
    )

    assert result["category"] == "FVTPL"
    assert result["carrying_value"] == 1150000  # Fair value
    assert result["unrealized_gain_loss"] == 0.0  # Changes go to P&L
    assert result["ecl_allowance"] == 0.0


def test_gaap_vs_ifrs_same_intent():
    """GAAP HTM vs IFRS Amortized Cost produce different results."""
    # Same position, different accounting standards
    position_gaap = {"intent": "HTM", "product_type": "FIXED_BOND"}
    position_ifrs = {
        "business_model": "HOLD_TO_COLLECT",
        "product_type": "FIXED_BOND",
    }

    # Market value decline
    market_value = 850000
    book_value = 1000000

    # GAAP: Uses impairment model (other than temporary)
    gaap_result = compute_gaap_valuation(position_gaap, market_value, book_value)

    # IFRS: Uses ECL model
    ifrs_result = compute_ifrs_valuation(
        position_ifrs,
        market_value,
        book_value,
        ecl_allowance=30000,  # ECL allowance
    )

    # Both carried at less than book, but different carrying values
    assert gaap_result["carrying_value"] == 850000  # Book - impairment
    assert ifrs_result["carrying_value"] == 970000  # Book - ECL

    # GAAP recognizes impairment, IFRS recognizes ECL
    assert gaap_result["impairment"] == 150000
    assert ifrs_result["ecl_allowance"] == 30000


def test_gaap_default_category():
    """GAAP defaults to AFS when no intent specified."""
    position = {"product_type": "FIXED_BOND"}  # No intent

    result = compute_gaap_valuation(
        position,
        market_value=1020000,
        book_value=1000000,
    )

    assert result["category"] == "AVAILABLE_FOR_SALE"
    assert result["carrying_value"] == 1020000  # Fair value


def test_ifrs_default_category():
    """IFRS defaults to FVTPL when no business model specified."""
    position = {"product_type": "FIXED_BOND"}  # No business model

    result = compute_ifrs_valuation(
        position,
        market_value=1020000,
        book_value=1000000,
    )

    # No business model specified -> defaults to FVTPL
    assert result["category"] == "FVTPL"
    assert result["carrying_value"] == 1020000
