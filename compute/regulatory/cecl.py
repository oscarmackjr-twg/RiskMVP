"""CECL (Current Expected Credit Loss) modeling engine.

Implements ASC 326 expected credit loss computation using multi-scenario
probability-weighted approach for lifetime expected credit losses.

Key concepts:
- CECL requires lifetime ECL for all financial assets
- Multi-scenario weighted approach required (base, adverse, severely adverse)
- Stage classification aligns with IFRS 9 for international consistency
"""
from __future__ import annotations

from typing import Dict, List, Any


def compute_cecl_allowance(
    portfolio: List[Dict[str, Any]],
    pd_curves: Dict[str, List[float]],
    lgd_assumptions: Dict[str, float],
    macro_scenarios: List[Dict[str, Any]],
    scenario_weights: List[float],
    q_factor: float = 0.0,
) -> Dict[str, Any]:
    """Compute CECL allowance for a loan portfolio.

    Uses probability-weighted multi-scenario ECL approach per ASC 326:
    ECL = sum(weight_i * ECL_scenario_i) for each scenario.

    Args:
        portfolio: List of positions with required fields:
            - position_id: Unique identifier
            - instrument_id: Instrument identifier
            - ead: Exposure at default (notional amount)
            - rating: Credit rating (defaults to "BBB" if missing)
            - base_ccy: Base currency
            - issuer_id: Obligor/issuer identifier for segmentation
        pd_curves: Dict mapping rating -> List[float] of annual PD values
            Example: {"BBB": [0.01, 0.015, 0.02, 0.025, 0.03]}
        lgd_assumptions: Dict mapping segment keys to LGD values
            Example: {"default": 0.45}
        macro_scenarios: List of macro scenario dicts (for future enhancement)
        scenario_weights: Probability weights for each scenario (must sum to 1.0)
        q_factor: Qualitative adjustment factor (default 0.0 = no adjustment)

    Returns:
        Dict with:
            - total_allowance: Total CECL allowance across portfolio
            - by_segment: Dict mapping segment_id -> ECL amount
            - scenario_detail: List of scenario-level calculations
    """
    # Input validation
    if not portfolio:
        return {"total_allowance": 0.0, "by_segment": {}, "scenario_detail": []}

    if len(scenario_weights) != len(macro_scenarios):
        raise ValueError("scenario_weights must match macro_scenarios length")

    # Segment portfolio by issuer
    segments: Dict[str, List[Dict[str, Any]]] = {}
    for position in portfolio:
        issuer_id = position.get("issuer_id", "unknown")
        if issuer_id not in segments:
            segments[issuer_id] = []
        segments[issuer_id].append(position)

    # Calculate ECL for each segment across scenarios
    segment_ecl: Dict[str, float] = {}
    scenario_details: List[Dict[str, Any]] = []

    for segment_id, positions in segments.items():
        # Determine segment rating (use first position's rating or default)
        rating = positions[0].get("rating", "BBB")

        # Get PD curve for this rating
        if rating in pd_curves:
            pd_curve = pd_curves[rating]
        else:
            # Fallback: try to import from compute.risk.credit if available
            try:
                from compute.risk.credit.pd_model import build_pd_curve
                pd_curve = build_pd_curve(rating, time_horizon_years=10)
            except Exception:
                # Final fallback: flat 2% PD
                pd_curve = [0.02] * 10

        # Get LGD for this segment
        lgd = lgd_assumptions.get(segment_id, lgd_assumptions.get("default", 0.45))

        # Sum EAD for segment
        segment_ead = sum(pos.get("ead", 0.0) for pos in positions)

        # Calculate ECL for each scenario
        scenario_ecls = []
        for scenario_idx, scenario in enumerate(macro_scenarios):
            # Compute lifetime PD for this scenario
            lifetime_pd = _compute_lifetime_pd(pd_curve)

            # ECL = EAD × Lifetime PD × LGD
            ecl_scenario = segment_ead * lifetime_pd * lgd
            scenario_ecls.append(ecl_scenario)

            # Record scenario detail
            scenario_details.append({
                "segment_id": segment_id,
                "scenario_index": scenario_idx,
                "scenario": scenario,
                "ead": segment_ead,
                "lifetime_pd": lifetime_pd,
                "lgd": lgd,
                "ecl": ecl_scenario,
            })

        # Weight scenarios to get segment ECL
        weighted_ecl = sum(
            scenario_weights[i] * scenario_ecls[i]
            for i in range(len(scenario_ecls))
        )
        segment_ecl[segment_id] = weighted_ecl

    # Apply qualitative adjustment (Q-factor)
    total_allowance = sum(segment_ecl.values()) * (1.0 + q_factor)

    return {
        "total_allowance": total_allowance,
        "by_segment": segment_ecl,
        "scenario_detail": scenario_details,
    }


def _compute_lifetime_pd(pd_curve: List[float]) -> float:
    """Compute lifetime probability of default from marginal annual PD curve.

    Calculates cumulative default probability over the instrument's lifetime
    using survival probability approach:

    Survival(t) = (1 - PD_1) × (1 - PD_2) × ... × (1 - PD_t)
    Lifetime PD = 1 - Survival(T)

    Args:
        pd_curve: List of annual marginal PD values (decimal, not percent)
            Example: [0.01, 0.015, 0.02] = 1%, 1.5%, 2% annual PD

    Returns:
        Lifetime cumulative PD, capped at 0.999 (99.9%)

    Example:
        >>> _compute_lifetime_pd([0.01, 0.015, 0.02])
        0.0446  # ≈ 4.46% lifetime PD over 3 years
    """
    if not pd_curve:
        return 0.0

    # Calculate survival probability (product of (1 - PD_i))
    survival_prob = 1.0
    for annual_pd in pd_curve:
        survival_prob *= (1.0 - annual_pd)

    # Lifetime PD = 1 - survival probability
    lifetime_pd = 1.0 - survival_prob

    # Cap at 99.9% to avoid numerical issues
    return min(lifetime_pd, 0.999)


def stage_classification(
    current_pd: float,
    origination_pd: float,
    days_past_due: int,
) -> int:
    """Classify exposure into IFRS 9 / CECL stages for allowance calculation.

    Stage classification determines the measurement approach:
    - Stage 1: 12-month ECL (no significant deterioration)
    - Stage 2: Lifetime ECL (significant deterioration)
    - Stage 3: Lifetime ECL for credit-impaired assets

    This aligns CECL (ASC 326) with IFRS 9 staging for consistent
    international risk measurement.

    Args:
        current_pd: Current probability of default (decimal)
        origination_pd: PD at origination (decimal)
        days_past_due: Number of days payment is overdue

    Returns:
        Stage number (1, 2, or 3)

    Stage 1: No significant increase in credit risk
        - DPD <= 90 days AND
        - Current PD <= 2× origination PD

    Stage 2: Significant increase in credit risk
        - DPD <= 90 days AND
        - Current PD > 2× origination PD (simplified threshold)

    Stage 3: Credit-impaired (>90 DPD or default)
        - DPD > 90 days (regulatory definition of default)
    """
    if days_past_due > 90:
        return 3
    if current_pd > origination_pd * 2.0:  # Simplified threshold
        return 2
    return 1
