"""Tests for VaR and Expected Shortfall calculations."""
import pytest
import numpy as np
from compute.risk.market.var import calculate_var_historical, calculate_var_parametric
from compute.risk.market.expected_shortfall import calculate_expected_shortfall


def test_var_historical_95():
    """Test historical VaR at 95% confidence level."""
    # Create sample returns distribution
    returns = [-0.05, -0.03, -0.02, -0.01, 0.00, 0.01, 0.02, 0.03, 0.04, 0.05]
    
    var = calculate_var_historical(returns, confidence_level=0.95)
    
    # 95% VaR should be around 5th percentile (worst 5%)
    # Expected to be between 0.03 and 0.05 (positive loss)
    assert var > 0, "VaR should be positive"
    assert 0.02 < var < 0.06, f"VaR 95% should be reasonable, got {var}"


def test_var_parametric():
    """Test parametric VaR matches normal distribution."""
    # Mean return and std dev
    mean = 0.0005  # 0.05% mean return
    std_dev = 0.02  # 2% volatility
    
    var = calculate_var_parametric(mean, std_dev, confidence_level=0.95)
    
    # For 95% confidence, z-score is approximately -1.645
    # VaR = -(mean + z * std_dev) = -(0.0005 - 1.645 * 0.02) = 0.0324
    expected_var = -(mean - 1.645 * std_dev)
    
    assert abs(var - expected_var) < 0.001, f"VaR should match parametric calculation"


def test_expected_shortfall_exceeds_var():
    """Test that ES >= VaR always (coherent risk measure property)."""
    # Generate random returns
    np.random.seed(42)
    returns = np.random.normal(-0.0005, 0.02, 1000).tolist()
    
    var = calculate_var_historical(returns, confidence_level=0.95)
    es = calculate_expected_shortfall(returns, confidence_level=0.95)
    
    assert es >= var, f"ES ({es}) should be >= VaR ({var})"
    print(f"VaR: {var:.4f}, ES: {es:.4f}, ES/VaR ratio: {es/var:.2f}")


def test_var_validation():
    """Test input validation for VaR functions."""
    # Empty returns list
    with pytest.raises(ValueError, match="Returns list cannot be empty"):
        calculate_var_historical([], confidence_level=0.95)
    
    # Confidence level out of range
    with pytest.raises(ValueError, match="Confidence level must be between 0 and 1"):
        calculate_var_historical([0.01, 0.02], confidence_level=1.5)


def test_parametric_var_zero_volatility():
    """Test parametric VaR with zero volatility."""
    var = calculate_var_parametric(mean=0.001, std_dev=0.0, confidence_level=0.95)
    
    # With zero volatility and positive mean, VaR should be 0 (no downside risk)
    assert var == 0, f"VaR with zero vol should be 0, got {var}"


def test_es_validation():
    """Test input validation for Expected Shortfall."""
    # Empty returns list
    with pytest.raises(ValueError, match="Returns list cannot be empty"):
        calculate_expected_shortfall([], confidence_level=0.95)
    
    # Confidence level out of range
    with pytest.raises(ValueError, match="Confidence level must be between 0 and 1"):
        calculate_expected_shortfall([0.01, 0.02], confidence_level=0.0)
