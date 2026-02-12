"""Abstract base class for all pricers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List


class AbstractPricer(ABC):
    """Base class for instrument pricers.

    All pricers must implement the `price()` method, which takes a position,
    instrument definition, market snapshot, list of measures, and scenario ID,
    and returns a dict of measure_name -> computed_value.
    """

    @abstractmethod
    def price(
        self,
        position: dict,
        instrument: dict,
        market_snapshot: dict,
        measures: List[str],
        scenario_id: str,
    ) -> Dict[str, float]:
        """Compute requested measures for a position under a scenario.

        Args:
            position: Position dict with position_id, attributes, etc.
            instrument: Instrument definition with terms, conventions, etc.
            market_snapshot: Market data snapshot with curves, fx_spots, etc.
            measures: List of measure names to compute (e.g. ["PV", "DV01"]).
            scenario_id: Scenario identifier (e.g. "BASE", "RATES_PARALLEL_1BP").

        Returns:
            Dict mapping measure name to computed float value.
        """
        ...
