"""Events related to portfolio lifecycle."""
from __future__ import annotations

from shared.events.base import BaseEvent


class PositionUpdated(BaseEvent):
    event_type: str = "portfolio.position_updated"
    source_service: str = "portfolio_svc"


class PortfolioRebalanced(BaseEvent):
    event_type: str = "portfolio.rebalanced"
    source_service: str = "portfolio_svc"
