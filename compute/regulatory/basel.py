"""Basel III capital calculations.

Implements standardized approach for Risk-Weighted Assets (RWA) calculation
and capital adequacy ratios per Basel III framework.

Key concepts:
- Standardized Approach uses fixed risk weights by counterparty type and rating
- RWA = Σ(EAD_i × RiskWeight_i) for each exposure
- Capital ratios: CET1, Tier 1, Total Capital relative to RWA
- Minimum requirements: CET1 ≥ 4.5%, Tier 1 ≥ 6%, Total ≥ 8%
"""
from __future__ import annotations

from typing import Dict, Any, List, Tuple


def compute_basel_rwa(
    portfolio: List[Dict[str, Any]],
    risk_weights: Dict[Tuple[str, str], float],
) -> Dict[str, Any]:
    """Compute Basel III Risk-Weighted Assets using standardized approach.

    Args:
        portfolio: List of positions with required fields:
            - position_id: Unique identifier
            - ead: Exposure at default (notional amount)
            - counterparty_type: SOVEREIGN, CORPORATE, RETAIL, UNRATED
            - rating: Credit rating (or "ANY" for unrated)
        risk_weights: Dict mapping (counterparty_type, rating) -> risk weight
            Example: {('CORPORATE', 'AAA'): 0.20, ('RETAIL', 'ANY'): 0.75}

    Returns:
        Dict with:
            - total_rwa: Total risk-weighted assets
            - by_counterparty_type: RWA aggregated by counterparty type
            - by_rating: RWA aggregated by rating
            - detail: List of position-level RWA calculations
    """
    if not portfolio:
        return {
            "total_rwa": 0.0,
            "by_counterparty_type": {},
            "by_rating": {},
            "detail": [],
        }

    # Aggregate by counterparty type and rating
    by_counterparty: Dict[str, float] = {}
    by_rating: Dict[str, float] = {}
    position_detail: List[Dict[str, Any]] = []

    total_rwa = 0.0

    for position in portfolio:
        position_id = position.get("position_id", "unknown")
        ead = position.get("ead", 0.0)
        counterparty_type = position.get("counterparty_type", "UNRATED")
        rating = position.get("rating", "UNRATED")

        # Get risk weight for this position
        risk_weight = get_risk_weight(counterparty_type, rating, risk_weights)

        # Compute position RWA
        position_rwa = ead * risk_weight

        # Aggregate
        total_rwa += position_rwa

        if counterparty_type not in by_counterparty:
            by_counterparty[counterparty_type] = 0.0
        by_counterparty[counterparty_type] += position_rwa

        if rating not in by_rating:
            by_rating[rating] = 0.0
        by_rating[rating] += position_rwa

        # Record detail
        position_detail.append({
            "position_id": position_id,
            "ead": ead,
            "counterparty_type": counterparty_type,
            "rating": rating,
            "risk_weight": risk_weight,
            "rwa": position_rwa,
        })

    return {
        "total_rwa": total_rwa,
        "by_counterparty_type": by_counterparty,
        "by_rating": by_rating,
        "detail": position_detail,
    }


def get_risk_weight(
    counterparty_type: str,
    rating: str,
    risk_weights: Dict[Tuple[str, str], float],
) -> float:
    """Get Basel III standardized approach risk weight for a position.

    Lookup order:
    1. Exact match: (counterparty_type, rating)
    2. Fallback: (counterparty_type, "ANY")
    3. Default: 1.00 (100% risk weight for unrated/unknown)

    Args:
        counterparty_type: SOVEREIGN, CORPORATE, RETAIL, UNRATED
        rating: Credit rating (AAA, AA, A, BBB, BB, B, CCC, etc.)
        risk_weights: Dict mapping (counterparty_type, rating) tuples to weights

    Returns:
        Risk weight as decimal (0.20 = 20%, 1.00 = 100%)

    Example:
        >>> weights = {('CORPORATE', 'AAA'): 0.20, ('CORPORATE', 'ANY'): 1.00}
        >>> get_risk_weight('CORPORATE', 'AAA', weights)
        0.20
        >>> get_risk_weight('CORPORATE', 'NR', weights)
        1.00
    """
    # Try exact match
    key = (counterparty_type, rating)
    if key in risk_weights:
        return risk_weights[key]

    # Try counterparty type with ANY rating
    fallback_key = (counterparty_type, "ANY")
    if fallback_key in risk_weights:
        return risk_weights[fallback_key]

    # Default to 100% risk weight per Basel III unrated default
    return 1.00


def compute_capital_ratios(
    total_rwa: float,
    tier1_capital: float,
    tier2_capital: float,
) -> Dict[str, float]:
    """Compute Basel III capital adequacy ratios.

    Capital ratios measure bank's capital relative to risk-weighted assets.
    Basel III minimum requirements:
    - CET1 (Common Equity Tier 1) ratio ≥ 4.5%
    - Tier 1 ratio ≥ 6.0%
    - Total capital ratio ≥ 8.0%

    Args:
        total_rwa: Total risk-weighted assets
        tier1_capital: Tier 1 capital (CET1 + AT1)
        tier2_capital: Tier 2 capital (subordinated debt, etc.)

    Returns:
        Dict with capital ratios as decimals:
            - cet1_ratio: Common Equity Tier 1 ratio
            - tier1_ratio: Tier 1 capital ratio
            - total_capital_ratio: Total capital ratio

    Example:
        >>> compute_capital_ratios(10_000_000, 800_000, 200_000)
        {'cet1_ratio': 0.08, 'tier1_ratio': 0.08, 'total_capital_ratio': 0.10}
    """
    if total_rwa == 0:
        # No RWA means no capital requirement
        return {
            "cet1_ratio": 0.0,
            "tier1_ratio": 0.0,
            "total_capital_ratio": 0.0,
        }

    # For this implementation, assume all Tier 1 capital is CET1
    # (In reality, Tier 1 = CET1 + AT1 Additional Tier 1)
    cet1_ratio = tier1_capital / total_rwa
    tier1_ratio = tier1_capital / total_rwa
    total_capital_ratio = (tier1_capital + tier2_capital) / total_rwa

    return {
        "cet1_ratio": cet1_ratio,
        "tier1_ratio": tier1_ratio,
        "total_capital_ratio": total_capital_ratio,
    }


def capital_adequacy_ratio(
    tier1_capital: float,
    tier2_capital: float,
    rwa: float,
) -> Dict[str, float]:
    """Calculate Basel III capital ratios (legacy function).

    DEPRECATED: Use compute_capital_ratios instead.

    Returns:
        Dict with CET1 ratio, Tier 1 ratio, Total Capital ratio.
    """
    if rwa == 0:
        raise ValueError("RWA cannot be zero")
    total_capital = tier1_capital + tier2_capital
    return {
        "tier1_ratio": tier1_capital / rwa,
        "total_capital_ratio": total_capital / rwa,
    }


def leverage_ratio(tier1_capital: float, total_exposure: float) -> float:
    """Calculate Basel III leverage ratio.

    LR = Tier 1 Capital / Total Exposure Measure
    Minimum requirement: 3%
    """
    if total_exposure == 0:
        raise ValueError("Total exposure cannot be zero")
    return tier1_capital / total_exposure
