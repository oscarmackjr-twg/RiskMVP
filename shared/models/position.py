"""Position domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class Position(BaseModel):
    position_id: str
    instrument_id: str
    portfolio_node_id: str
    product_type: str
    quantity: float = 1.0
    base_ccy: str = "USD"
    attributes: Dict[str, Any] = Field(default_factory=dict)


class PositionSnapshot(BaseModel):
    position_snapshot_id: str
    as_of_time: datetime
    portfolio_node_id: str
    payload_hash: str
    created_at: Optional[datetime] = None
