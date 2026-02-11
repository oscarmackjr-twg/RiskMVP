"""Pricer registry - replaces if/elif dispatch chain in worker.py."""
from __future__ import annotations

from typing import Callable, Dict, List

# Type alias for pricer functions (backward-compatible with existing function-based pricers)
PricerFn = Callable[
    [dict, dict, dict, List[str], str],  # position, instrument, market_snapshot, measures, scenario_id
    Dict[str, float],
]

# Registry: product_type -> pricer function
_REGISTRY: Dict[str, PricerFn] = {}


def register(product_type: str, pricer_fn: PricerFn) -> None:
    """Register a pricer function for a product type."""
    _REGISTRY[product_type] = pricer_fn


def get_pricer(product_type: str) -> PricerFn:
    """Look up the pricer function for a product type.

    Raises:
        ValueError: If no pricer is registered for the product type.
    """
    if product_type not in _REGISTRY:
        raise ValueError(f"No pricer registered for product_type: {product_type}")
    return _REGISTRY[product_type]


def registered_types() -> List[str]:
    """Return all registered product types."""
    return list(_REGISTRY.keys())


# Auto-register existing pricers on import
def _bootstrap() -> None:
    from compute.pricers.fx_fwd import price_fx_fwd
    from compute.pricers.loan import price_loan
    from compute.pricers.bond import price_bond
    from compute.pricers.derivatives import price_derivatives
    from compute.pricers.structured import price_structured

    register("FX_FWD", price_fx_fwd)
    register("AMORT_LOAN", price_loan)
    register("FIXED_BOND", price_bond)
    register("DERIVATIVES", price_derivatives)
    register("STRUCTURED", price_structured)


_bootstrap()
