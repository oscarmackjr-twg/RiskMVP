"""Loss Given Default (LGD) models."""
from __future__ import annotations

from typing import Dict, Any


def workout_lgd(
    collateral_value: float,
    exposure: float,
    recovery_costs: float = 0.0,
    time_to_recovery_years: float = 1.0,
    discount_rate: float = 0.05,
) -> float:
    """Calculate LGD using workout/recovery approach.

    LGD = 1 - (Collateral - Costs) * DF / Exposure
    """
    raise NotImplementedError("Workout LGD not yet implemented")


def market_lgd(rating: str, seniority: str = "SENIOR_SECURED") -> float:
    """Look up market-implied LGD from rating and seniority."""
    raise NotImplementedError("Market LGD not yet implemented")
