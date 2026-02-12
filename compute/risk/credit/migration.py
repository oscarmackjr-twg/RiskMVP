"""Rating transition/migration matrix analytics."""
from __future__ import annotations

from typing import List, Dict


def get_transition_matrix(source: str = "SP") -> List[List[float]]:
    """Return a rating transition probability matrix.

    Stub - to be loaded from reference data.
    """
    raise NotImplementedError("Transition matrix loading not yet implemented")


def migration_pnl(
    current_rating: str,
    position_value: float,
    spread_curves: Dict[str, float],
) -> Dict[str, float]:
    """Calculate P&L impact for each possible rating migration.

    Returns dict mapping target_rating -> P&L impact.
    """
    raise NotImplementedError("Migration P&L not yet implemented")
