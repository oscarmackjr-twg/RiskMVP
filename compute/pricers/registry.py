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
# Uses try/except per pricer so that pricers with heavy dependencies (e.g. QuantLib)
# don't prevent other pricers from registering when those dependencies are absent.
def _bootstrap() -> None:
    _pricers = [
        ("FX_FWD", "compute.pricers.fx_fwd", "price_fx_fwd"),
        ("AMORT_LOAN", "compute.pricers.loan", "price_loan"),
        ("FIXED_BOND", "compute.pricers.bond", "price_bond"),
        ("CALLABLE_BOND", "compute.pricers.callable_bond", "price_callable_bond"),
        ("PUTABLE_BOND", "compute.pricers.putable_bond", "price_putable_bond"),
        ("FLOATING_RATE", "compute.pricers.floating_rate", "price_floating_rate"),
        ("DERIVATIVES", "compute.pricers.derivatives", "price_derivatives"),
        ("STRUCTURED", "compute.pricers.structured", "price_structured"),
        ("ABS_MBS", "compute.pricers.abs_mbs", "price_abs_mbs"),
    ]
    import importlib
    for product_type, module_path, fn_name in _pricers:
        try:
            mod = importlib.import_module(module_path)
            register(product_type, getattr(mod, fn_name))
        except Exception as e:
            import sys
            print(f"[registry] skipping {product_type}: {e}", file=sys.stderr)


_bootstrap()
