"""Monte Carlo path generation using interest rate models.

Generates interest rate paths for scenario analysis and VaR calculation.
Supports Hull-White, Vasicek, and CIR models using Euler discretization.
"""
from __future__ import annotations

from typing import Dict, List
import numpy as np
import QuantLib as ql


def generate_rate_paths(
    model: str,
    num_paths: int,
    time_horizon_years: int,
    time_steps: int,
    model_params: Dict,
) -> np.ndarray:
    """
    Generate interest rate paths using stochastic interest rate models.

    Uses Euler discretization for path generation. For production use,
    consider more sophisticated schemes (Milstein, exact solutions).

    Args:
        model: Model type ('HULL_WHITE', 'VASICEK', 'CIR')
        num_paths: Number of paths to generate
        time_horizon_years: Simulation horizon in years
        time_steps: Number of time steps
        model_params: Model-specific parameters
            For HULL_WHITE: {'a': mean_reversion, 'sigma': volatility, 'rate': initial_rate}
            For VASICEK: {'a': mean_reversion, 'b': long_term_mean, 'sigma': volatility, 'rate': initial_rate}
            For CIR: {'a': mean_reversion, 'b': long_term_mean, 'sigma': volatility, 'rate': initial_rate}

    Returns:
        NumPy array of shape (num_paths, time_steps + 1) containing interest rate paths
        Each row is a path, each column is a time point (including t=0)

    Example:
        >>> params = {'a': 0.03, 'sigma': 0.12, 'rate': 0.025}
        >>> paths = generate_rate_paths('HULL_WHITE', 10, 5, 60, params)
        >>> print(f"Paths shape: {paths.shape}")
        Paths shape: (10, 61)
    """
    model = model.upper()

    # Time step size
    dt = time_horizon_years / time_steps

    # Generate paths based on model type
    if model == 'HULL_WHITE':
        paths = _generate_hull_white_paths(num_paths, time_steps, dt, model_params)
    elif model == 'VASICEK':
        paths = _generate_vasicek_paths(num_paths, time_steps, dt, model_params)
    elif model == 'CIR':
        paths = _generate_cir_paths(num_paths, time_steps, dt, model_params)
    else:
        raise ValueError(f"Unknown model: {model}. Supported: HULL_WHITE, VASICEK, CIR")

    return paths


def _generate_hull_white_paths(
    num_paths: int,
    time_steps: int,
    dt: float,
    params: Dict,
) -> np.ndarray:
    """Generate paths using Hull-White one-factor model.

    Hull-White: dr = [theta(t) - a*r]dt + sigma*dW

    For simplicity, we use constant theta = a*r0 (mean-reverting to initial rate).
    """
    a = params.get('a', 0.03)  # Mean reversion speed
    sigma = params.get('sigma', 0.12)  # Volatility
    r0 = params.get('rate', 0.025)  # Initial rate

    # Constant theta for mean reversion to r0
    theta = a * r0

    paths = np.zeros((num_paths, time_steps + 1))
    paths[:, 0] = r0

    # Generate paths using Euler discretization
    for i in range(num_paths):
        for t in range(time_steps):
            dW = np.random.normal(0, np.sqrt(dt))
            dr = (theta - a * paths[i, t]) * dt + sigma * dW
            paths[i, t + 1] = paths[i, t] + dr

    return paths


def _generate_vasicek_paths(
    num_paths: int,
    time_steps: int,
    dt: float,
    params: Dict,
) -> np.ndarray:
    """Generate paths using Vasicek model.

    Vasicek: dr = a(b - r)dt + sigma * dW
    """
    a = params.get('a', 0.1)  # Mean reversion speed
    b = params.get('b', 0.05)  # Long-term mean
    sigma = params.get('sigma', 0.01)  # Volatility
    r0 = params.get('rate', 0.025)  # Initial rate

    paths = np.zeros((num_paths, time_steps + 1))
    paths[:, 0] = r0

    # Generate paths using Euler discretization
    for i in range(num_paths):
        for t in range(time_steps):
            dW = np.random.normal(0, np.sqrt(dt))
            dr = a * (b - paths[i, t]) * dt + sigma * dW
            paths[i, t + 1] = paths[i, t] + dr

    return paths


def _generate_cir_paths(
    num_paths: int,
    time_steps: int,
    dt: float,
    params: Dict,
) -> np.ndarray:
    """Generate paths using Cox-Ingersoll-Ross (CIR) model.

    CIR: dr = a(b - r)dt + sigma * sqrt(r) * dW

    Feller condition: 2*a*b >= sigma^2 ensures positive rates.
    """
    a = params.get('a', 0.15)  # Mean reversion speed
    b = params.get('b', 0.05)  # Long-term mean
    sigma = params.get('sigma', 0.05)  # Volatility
    r0 = params.get('rate', 0.025)  # Initial rate

    paths = np.zeros((num_paths, time_steps + 1))
    paths[:, 0] = r0

    # Generate paths using Euler discretization with reflection at zero
    for i in range(num_paths):
        for t in range(time_steps):
            dW = np.random.normal(0, np.sqrt(dt))
            # Ensure rate stays positive (reflection)
            r_t = max(paths[i, t], 1e-8)
            dr = a * (b - r_t) * dt + sigma * np.sqrt(r_t) * dW
            paths[i, t + 1] = max(r_t + dr, 0)  # Keep positive

    return paths
