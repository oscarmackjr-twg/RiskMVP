"""Portfolio domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class PortfolioNode(BaseModel):
    node_id: str
    name: str
    parent_id: Optional[str] = None
    node_type: str = "PORTFOLIO"  # PORTFOLIO, BOOK, DESK, STRATEGY
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class Holding(BaseModel):
    holding_id: str
    portfolio_node_id: str
    instrument_id: str
    quantity: float
    cost_basis: Optional[float] = None
    acquisition_date: Optional[datetime] = None


class PortfolioTag(BaseModel):
    tag_id: str
    portfolio_node_id: str
    tag_key: str
    tag_value: str


class PortfolioSnapshot(BaseModel):
    snapshot_id: str
    portfolio_node_id: str
    as_of_time: datetime
    holdings: List[Holding] = Field(default_factory=list)
    total_market_value: Optional[float] = None
