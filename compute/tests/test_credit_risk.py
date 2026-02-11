"""Tests for credit risk analytics (PD model and expected loss)."""
import pytest
from compute.risk.credit.pd_model import build_pd_curve, through_the_cycle_pd
from compute.risk.credit.expected_loss import calculate_expected_loss, calculate_unexpected_loss


def test_pd_curve_construction():
    """Test PD curve construction from BBB rating."""
    pd_curve = build_pd_curve('BBB', 5)
    
    # Check length
    assert len(pd_curve) == 5, "Should return 5 years of PDs"
    
    # Check Year 1 PD is approximately 0.20% (0.0020)
    assert 0.0015 < pd_curve[0] < 0.0025, f"Year 1 PD should be ~0.20%, got {pd_curve[0]}"
    
    # Check PDs are positive
    assert all(pd >= 0 for pd in pd_curve), "All PDs should be non-negative"


def test_expected_loss_calculation():
    """Test expected loss formula: EL = PD × LGD × EAD."""
    # Example: 2% PD, 40% LGD, $100K EAD
    el = calculate_expected_loss(pd=0.02, lgd=0.40, ead=100_000)
    
    # EL = 0.02 × 0.40 × 100,000 = 800
    assert 799 < el < 801, f"Expected $800, got ${el}"


def test_unexpected_loss():
    """Test unexpected loss formula: UL = EAD × LGD × sqrt(PD × (1 - PD))."""
    # Example: 2% PD, 40% LGD, $100K EAD
    ul = calculate_unexpected_loss(pd=0.02, lgd=0.40, ead=100_000)
    
    # UL = 100,000 × 0.40 × sqrt(0.02 × 0.98) = approx 5,600
    expected_ul = 100_000 * 0.40 * (0.02 * 0.98) ** 0.5
    assert abs(ul - expected_ul) < 10, f"UL mismatch: expected {expected_ul}, got {ul}"


def test_pd_curve_rating_validation():
    """Test that invalid ratings raise errors."""
    with pytest.raises(ValueError, match="Unknown rating"):
        build_pd_curve('INVALID', 5)


def test_expected_loss_validation():
    """Test input validation for expected loss."""
    # PD out of range
    with pytest.raises(ValueError, match="PD must be between 0 and 1"):
        calculate_expected_loss(pd=1.5, lgd=0.40, ead=100_000)
    
    # LGD out of range
    with pytest.raises(ValueError, match="LGD must be between 0 and 1"):
        calculate_expected_loss(pd=0.02, lgd=1.5, ead=100_000)
    
    # Negative EAD
    with pytest.raises(ValueError, match="EAD must be non-negative"):
        calculate_expected_loss(pd=0.02, lgd=0.40, ead=-1000)
