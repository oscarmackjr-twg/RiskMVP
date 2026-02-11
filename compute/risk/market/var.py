"""Value at Risk (VaR) calculation.

Supports historical simulation, parametric (variance-covariance),
and Monte Carlo VaR methods.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np
from scipy import stats


def calculate_var_historical(
    returns: List[float],
    confidence_level: float = 0.95,
) -> float:
    """Calculate VaR using historical simulation.

    Historical VaR from empirical return distribution.

    Args:
        returns: Historical return observations (as decimals, e.g. 0.01 = 1%).
        confidence_level: Confidence level (e.g. 0.90, 0.95, 0.99).

    Returns:
        VaR amount (positive number representing potential loss).

    Raises:
        ValueError: If returns list is empty or confidence_level out of range.

    Example:
        >>> returns = [-0.02, -0.01, 0.00, 0.01, 0.02]
        >>> var = calculate_var_historical(returns, 0.95)
        >>> print(f"VaR 95%: {var:.4f}")
    """
    if not returns:
        raise ValueError("Returns list cannot be empty")
    if not (0 < confidence_level < 1):
        raise ValueError(f"Confidence level must be between 0 and 1, got {confidence_level}")

    # Sort returns ascending (worst losses first)
    sorted_returns = sorted(returns)

    # Find percentile: VaR at (1 - confidence_level) percentile
    percentile = (1 - confidence_level) * 100
    var_return = np.percentile(sorted_returns, percentile)

    # VaR is positive loss magnitude
    return -var_return


def calculate_var_parametric(
    mean: float,
    std_dev: float,
    confidence_level: float = 0.95,
) -> float:
    """Calculate parametric (variance-covariance) VaR.

    Parametric VaR assuming normal distribution.

    Args:
        mean: Mean return (decimal, e.g. 0.001 = 0.1%).
        std_dev: Standard deviation of returns (decimal).
        confidence_level: Confidence level (e.g. 0.95, 0.99).

    Returns:
        VaR amount (positive number representing potential loss).

    Raises:
        ValueError: If std_dev is negative or confidence_level out of range.

    Example:
        >>> var = calculate_var_parametric(0.0005, 0.02, 0.95)
        >>> print(f"VaR 95%: {var:.4f}")
    """
    if std_dev < 0:
        raise ValueError(f"Standard deviation must be non-negative, got {std_dev}")
    if not (0 < confidence_level < 1):
        raise ValueError(f"Confidence level must be between 0 and 1, got {confidence_level}")

    # Handle zero std_dev case
    if std_dev == 0:
        return max(0, -mean)

    # Use scipy to get z-score for confidence level
    # ppf gives the inverse CDF (quantile function)
    z_score = stats.norm.ppf(1 - confidence_level)

    # VaR = -(mean + z_score * std_dev)
    # z_score is negative for typical confidence levels
    var = -(mean + z_score * std_dev)

    return max(0, var)


# Legacy function names for backward compatibility
def historical_var(
    pnl_series: List[float],
    confidence_level: float = 0.95,
) -> float:
    """Calculate VaR using historical simulation (legacy name).

    Args:
        pnl_series: Historical P&L observations.
        confidence_level: Confidence level (e.g. 0.95, 0.99).

    Returns:
        VaR amount (positive number representing potential loss).
    """
    return calculate_var_historical(pnl_series, confidence_level)


def parametric_var(
    portfolio_value: float,
    portfolio_volatility: float,
    confidence_level: float = 0.95,
    holding_period_days: int = 1,
) -> float:
    """Calculate parametric (variance-covariance) VaR (legacy name).

    Args:
        portfolio_value: Current portfolio market value.
        portfolio_volatility: Portfolio return volatility (annualized).
        confidence_level: Confidence level.
        holding_period_days: Holding period in trading days.

    Returns:
        VaR amount.
    """
    # Scale volatility for holding period
    # Assume 252 trading days per year
    period_volatility = portfolio_volatility * np.sqrt(holding_period_days / 252.0)

    # Calculate VaR in return terms
    var_return = calculate_var_parametric(0, period_volatility, confidence_level)

    # Convert to dollar amount
    return var_return * portfolio_value


def monte_carlo_var(
    simulated_pnls: List[float],
    confidence_level: float = 0.95,
) -> float:
    """Calculate VaR from Monte Carlo simulated P&L distribution (legacy name)."""
    return calculate_var_historical(simulated_pnls, confidence_level)
