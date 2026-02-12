"""Market depth analytics."""
from __future__ import annotations

from typing import List, Dict, Any


def market_impact(order_size: float, market_depth: List[Dict[str, Any]]) -> float:
    """Estimate market impact of an order given depth of book.

    Stub - to be implemented with order book simulation.
    """
    raise NotImplementedError("Market impact estimation not yet implemented")
