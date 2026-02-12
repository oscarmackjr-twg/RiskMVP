"""Risk-Weighted Assets (RWA) calculation."""
from __future__ import annotations

from typing import Dict, Any, List


# Basel III Standardized Approach risk weights by exposure class
STANDARDIZED_RISK_WEIGHTS = {
    "SOVEREIGN_AAA": 0.0,
    "SOVEREIGN_AA": 0.0,
    "SOVEREIGN_A": 0.20,
    "SOVEREIGN_BBB": 0.50,
    "SOVEREIGN_BB": 1.00,
    "BANK_AAA": 0.20,
    "BANK_A": 0.50,
    "CORPORATE_AAA": 0.20,
    "CORPORATE_A": 0.50,
    "CORPORATE_BBB": 0.75,
    "CORPORATE_BB": 1.00,
    "CORPORATE_UNRATED": 1.00,
    "RETAIL": 0.75,
    "RESIDENTIAL_MORTGAGE": 0.35,
    "COMMERCIAL_REAL_ESTATE": 1.50,
}


def standardized_rwa(exposure: float, exposure_class: str) -> float:
    """Calculate RWA under Standardized Approach.

    RWA = Exposure * Risk Weight
    """
    rw = STANDARDIZED_RISK_WEIGHTS.get(exposure_class, 1.0)
    return exposure * rw


def irb_rwa(pd: float, lgd: float, ead: float, maturity_years: float = 2.5) -> float:
    """Calculate RWA under Internal Ratings-Based (IRB) approach.

    Stub - simplified; full implementation requires correlation function.
    """
    raise NotImplementedError("IRB RWA calculation not yet implemented")
