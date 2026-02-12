"""GAAP and IFRS valuation framework.

Implements classification and valuation logic for financial instruments
under US GAAP (ASC 320) and IFRS 9 standards.

Key concepts:
- GAAP: HTM (amortized cost), AFS (fair value through OCI), Trading (fair value through P&L)
- IFRS 9: Amortized Cost, FVOCI, FVTPL based on business model and SPPI test
- Impairment: GAAP uses "other than temporary" impairment, IFRS uses ECL
"""
from __future__ import annotations

from typing import Dict, Any


def classify_gaap_category(position: Dict[str, Any]) -> str:
    """Classify position into GAAP category per ASC 320.

    GAAP categories based on management intent at acquisition:
    - Held-to-Maturity (HTM): Intent and ability to hold until maturity
    - Available-for-Sale (AFS): May be sold before maturity
    - Trading: Held for short-term profit

    Args:
        position: Position dict with optional "intent" field
            intent values: "HTM", "AFS", "TRADING"

    Returns:
        GAAP category: "HELD_TO_MATURITY", "AVAILABLE_FOR_SALE", or "TRADING"

    Default: "AVAILABLE_FOR_SALE" if no intent specified
    """
    intent = position.get("intent", "").upper()

    if intent == "HTM":
        return "HELD_TO_MATURITY"
    elif intent == "TRADING":
        return "TRADING"
    else:
        # Default to AFS (most common for investment portfolios)
        return "AVAILABLE_FOR_SALE"


def classify_ifrs_category(
    position: Dict[str, Any],
    business_model: str = None,
) -> str:
    """Classify position into IFRS 9 category.

    IFRS 9 classification based on:
    1. Business model (hold to collect, hold and sell, trading)
    2. Contractual cash flow characteristics (SPPI test)

    Categories:
    - Amortized Cost: Business model is hold-to-collect AND cash flows are SPPI
    - FVOCI: Business model is hold-and-sell AND cash flows are SPPI
    - FVTPL: All other instruments (failing SPPI or trading)

    Args:
        position: Position dict with optional "business_model" and "product_type"
        business_model: Override business model
            Values: "HOLD_TO_COLLECT", "HOLD_AND_SELL", "TRADING"

    Returns:
        IFRS category: "AMORTIZED_COST", "FVOCI", or "FVTPL"
    """
    # Get business model from parameter or position metadata
    if business_model is None:
        business_model = position.get("business_model", "").upper()

    # Simplified SPPI test: bonds and loans are SPPI, derivatives are not
    product_type = position.get("product_type", "").upper()
    is_sppi = product_type in [
        "FIXED_BOND",
        "AMORT_LOAN",
        "FLOATING_RATE_NOTE",
        "CALLABLE_BOND",
        "PUTABLE_BOND",
    ]

    # Classification logic
    if business_model == "HOLD_TO_COLLECT" and is_sppi:
        return "AMORTIZED_COST"
    elif business_model == "HOLD_AND_SELL" and is_sppi:
        return "FVOCI"
    else:
        # Default to FVTPL (fair value through P&L)
        return "FVTPL"


def compute_impairment(
    position: Dict[str, Any],
    market_value: float,
    book_value: float,
    category: str,
) -> float:
    """Compute GAAP impairment for a position.

    GAAP impairment recognition (ASC 320):
    - HTM: Recognize impairment if decline is "other than temporary"
    - AFS: Unrealized losses go to OCI (no impairment to book value)
    - Trading: Fair value changes go to P&L (no impairment concept)

    Simplified impairment test for HTM:
    - If market_value < book_value × 0.90 (>10% decline), recognize impairment

    Args:
        position: Position dict
        market_value: Current market/fair value
        book_value: Book value (amortized cost)
        category: GAAP category from classify_gaap_category

    Returns:
        Impairment amount (positive number = loss)
    """
    if category != "HELD_TO_MATURITY":
        # Only HTM securities have impairment to book value
        return 0.0

    # Simplified "other than temporary" impairment test
    # Real implementation would consider:
    # - Duration and severity of decline
    # - Issuer credit deterioration
    # - Intent/ability to hold to recovery
    impairment_threshold = book_value * 0.90

    if market_value < impairment_threshold:
        # Recognize impairment = book value - market value
        return book_value - market_value
    else:
        return 0.0


def compute_gaap_valuation(
    position: Dict[str, Any],
    market_value: float,
    book_value: float,
) -> Dict[str, Any]:
    """Compute GAAP valuation and carrying value.

    Valuation by category:
    - HTM: Carrying value = book value - impairment
    - AFS: Carrying value = market value, unrealized gain/loss in OCI
    - Trading: Carrying value = market value, realized gain/loss in P&L

    Args:
        position: Position dict with intent metadata
        market_value: Current fair value
        book_value: Amortized cost basis

    Returns:
        Dict with:
            - category: GAAP category
            - carrying_value: Balance sheet value
            - unrealized_gain_loss: Unrealized gain/loss (for AFS, in OCI)
            - realized_gain_loss: Realized gain/loss (for Trading, in P&L)
            - impairment: Impairment charge (for HTM)
    """
    category = classify_gaap_category(position)

    if category == "HELD_TO_MATURITY":
        # HTM: Amortized cost less impairment
        impairment = compute_impairment(position, market_value, book_value, category)
        carrying_value = book_value - impairment

        return {
            "category": category,
            "carrying_value": carrying_value,
            "unrealized_gain_loss": 0.0,
            "realized_gain_loss": 0.0,
            "impairment": impairment,
        }

    elif category == "AVAILABLE_FOR_SALE":
        # AFS: Fair value, unrealized gain/loss in OCI
        unrealized_gl = market_value - book_value

        return {
            "category": category,
            "carrying_value": market_value,
            "unrealized_gain_loss": unrealized_gl,
            "realized_gain_loss": 0.0,
            "impairment": 0.0,
        }

    else:  # TRADING
        # Trading: Fair value, realized gain/loss in P&L
        realized_gl = market_value - book_value

        return {
            "category": category,
            "carrying_value": market_value,
            "unrealized_gain_loss": 0.0,
            "realized_gain_loss": realized_gl,
            "impairment": 0.0,
        }


def compute_ifrs_valuation(
    position: Dict[str, Any],
    market_value: float,
    book_value: float,
    ecl_allowance: float = 0.0,
) -> Dict[str, Any]:
    """Compute IFRS 9 valuation and carrying value.

    Valuation by category:
    - Amortized Cost: Carrying value = book value - ECL allowance
    - FVOCI: Carrying value = market value, unrealized gain/loss in OCI
    - FVTPL: Carrying value = market value

    Args:
        position: Position dict with business_model and product_type
        market_value: Current fair value
        book_value: Amortized cost basis
        ecl_allowance: Expected credit loss allowance (for Amortized Cost)

    Returns:
        Dict with:
            - category: IFRS 9 category
            - carrying_value: Balance sheet value
            - unrealized_gain_loss: Unrealized gain/loss (for FVOCI, in OCI)
            - ecl_allowance: ECL allowance (for Amortized Cost)
    """
    category = classify_ifrs_category(position)

    if category == "AMORTIZED_COST":
        # Amortized cost less ECL
        carrying_value = book_value - ecl_allowance

        return {
            "category": category,
            "carrying_value": carrying_value,
            "unrealized_gain_loss": 0.0,
            "ecl_allowance": ecl_allowance,
        }

    elif category == "FVOCI":
        # Fair value through OCI
        unrealized_gl = market_value - book_value

        return {
            "category": category,
            "carrying_value": market_value,
            "unrealized_gain_loss": unrealized_gl,
            "ecl_allowance": 0.0,
        }

    else:  # FVTPL
        # Fair value through P&L
        return {
            "category": category,
            "carrying_value": market_value,
            "unrealized_gain_loss": 0.0,
            "ecl_allowance": 0.0,
        }
