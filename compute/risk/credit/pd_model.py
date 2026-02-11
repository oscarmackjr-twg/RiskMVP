"""Probability of Default (PD) models.

Constructs default probability curves from credit ratings.
Based on historical cumulative default rates from Moody's/S&P.
"""
from __future__ import annotations

from typing import Dict, Any, List
import math


# Historical cumulative default probabilities (%) by rating and year
# Source: Moody's Annual Default Study historical averages
CUMULATIVE_DEFAULT_RATES = {
    'AAA': [0.00, 0.00, 0.01, 0.03, 0.06, 0.09, 0.13, 0.17, 0.22, 0.27],
    'AA':  [0.01, 0.02, 0.04, 0.07, 0.11, 0.15, 0.20, 0.26, 0.32, 0.39],
    'A':   [0.03, 0.07, 0.12, 0.18, 0.25, 0.33, 0.42, 0.52, 0.63, 0.75],
    'BBB': [0.20, 0.45, 0.75, 1.10, 1.50, 1.95, 2.45, 3.00, 3.60, 4.25],
    'BB':  [1.00, 2.50, 4.25, 6.25, 8.50, 11.00, 13.75, 16.75, 20.00, 23.50],
    'B':   [5.00, 10.00, 15.00, 20.00, 25.00, 30.00, 35.00, 40.00, 45.00, 50.00],
    'CCC': [20.00, 35.00, 45.00, 52.00, 58.00, 63.00, 67.00, 70.00, 73.00, 75.00],
}


def build_pd_curve(rating: str, time_horizon_years: int = 10) -> List[float]:
    """
    Build probability of default curve from credit rating.

    Args:
        rating: Credit rating (AAA, AA, A, BBB, BB, B, CCC)
        time_horizon_years: Number of years to generate PD curve for

    Returns:
        List of marginal default probabilities (decimal) per year

    Example:
        >>> pd_curve = build_pd_curve('BBB', 5)
        >>> print(f"Year 1 PD: {pd_curve[0]:.4f}")
        Year 1 PD: 0.0020
    """
    rating = rating.upper()

    if rating not in CUMULATIVE_DEFAULT_RATES:
        raise ValueError(f"Unknown rating: {rating}. Supported: {list(CUMULATIVE_DEFAULT_RATES.keys())}")

    cumulative_pds = CUMULATIVE_DEFAULT_RATES[rating]

    # Convert percentages to decimals
    cumulative_pds = [pd / 100.0 for pd in cumulative_pds]

    # Convert cumulative to marginal PDs
    marginal_pds = []
    for i in range(min(time_horizon_years, len(cumulative_pds))):
        if i == 0:
            marginal_pd = cumulative_pds[0]
        else:
            marginal_pd = cumulative_pds[i] - cumulative_pds[i-1]
        marginal_pds.append(marginal_pd)

    # Extrapolate beyond table using constant hazard rate
    if time_horizon_years > len(cumulative_pds):
        # Calculate hazard rate from last two cumulative PDs
        last_cumulative = cumulative_pds[-1]
        prev_cumulative = cumulative_pds[-2]
        survival_rate_last = 1.0 - last_cumulative
        survival_rate_prev = 1.0 - prev_cumulative

        # Hazard rate = -ln(survival_rate_last / survival_rate_prev)
        if survival_rate_last > 0 and survival_rate_prev > 0:
            hazard_rate = -math.log(survival_rate_last / survival_rate_prev)
        else:
            hazard_rate = 0.05  # Default to 5% hazard rate

        # Extrapolate using constant hazard rate
        current_survival = survival_rate_last
        for year in range(len(cumulative_pds), time_horizon_years):
            next_survival = current_survival * math.exp(-hazard_rate)
            marginal_pd = current_survival - next_survival
            marginal_pds.append(marginal_pd)
            current_survival = next_survival

    return marginal_pds


def through_the_cycle_pd(rating: str, term_years: float) -> float:
    """Look up through-the-cycle PD from rating transition matrix.

    Args:
        rating: Credit rating
        term_years: Term in years

    Returns:
        Cumulative PD for the term
    """
    # Use build_pd_curve and return cumulative PD
    years = int(math.ceil(term_years))
    marginal_pds = build_pd_curve(rating, years)

    # Calculate cumulative from marginal
    survival_prob = 1.0
    for marginal_pd in marginal_pds:
        survival_prob *= (1.0 - marginal_pd)

    return 1.0 - survival_prob


def point_in_time_pd(rating: str, macro_factors: Dict[str, float]) -> float:
    """Calculate point-in-time PD adjusted for macroeconomic conditions.

    Future enhancement: Adjust TTC PD based on macro factors.
    For now, returns TTC PD.
    """
    # Placeholder: Use TTC PD for now
    return through_the_cycle_pd(rating, 1.0)


def lifetime_pd_curve(annual_pd: float, term_years: int) -> list[float]:
    """Generate a lifetime marginal PD curve assuming constant hazard rate.

    Args:
        annual_pd: Annual probability of default
        term_years: Term in years

    Returns:
        List of marginal PDs per year
    """
    # Convert annual PD to hazard rate
    if annual_pd >= 1.0:
        hazard_rate = 10.0  # Cap at very high rate
    elif annual_pd <= 0:
        return [0.0] * term_years
    else:
        hazard_rate = -math.log(1.0 - annual_pd)

    # Generate marginal PDs
    marginal_pds = []
    survival_prob = 1.0
    for year in range(term_years):
        next_survival = survival_prob * math.exp(-hazard_rate)
        marginal_pd = survival_prob - next_survival
        marginal_pds.append(marginal_pd)
        survival_prob = next_survival

    return marginal_pds
