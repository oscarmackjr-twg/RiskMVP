"""Market data domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class CurveType(str, Enum):
    DISCOUNT = "DISCOUNT"
    SPREAD = "SPREAD"
    FORWARD = "FORWARD"
    BASIS = "BASIS"


class CurveNode(BaseModel):
    tenor: str
    zero_rate: float


class Curve(BaseModel):
    curve_id: str
    curve_type: CurveType
    nodes: List[CurveNode]


class FxSpot(BaseModel):
    pair: str
    spot: float
    ts: datetime


class CreditSpread(BaseModel):
    issuer_id: str
    rating: str
    sector: str
    tenor: str
    spread_bps: float
    as_of_time: datetime


class MarketDataSnapshot(BaseModel):
    snapshot_id: str
    as_of_time: datetime
    vendor: str
    universe_id: str
    fx_spots: List[FxSpot] = Field(default_factory=list)
    curves: List[Curve] = Field(default_factory=list)
    credit_spreads: List[CreditSpread] = Field(default_factory=list)
