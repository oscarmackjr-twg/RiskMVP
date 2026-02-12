"""Performance and attribution domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Dict, List


class ReturnSeries(BaseModel):
    portfolio_node_id: str
    period_start: date
    period_end: date
    total_return: float
    income_return: Optional[float] = None
    price_return: Optional[float] = None
    currency_return: Optional[float] = None


class AttributionResult(BaseModel):
    result_id: str
    portfolio_node_id: str
    period_start: date
    period_end: date
    total_return: float
    duration_effect: Optional[float] = None
    spread_effect: Optional[float] = None
    selection_effect: Optional[float] = None
    allocation_effect: Optional[float] = None
    residual: Optional[float] = None


class BenchmarkDefinition(BaseModel):
    benchmark_id: str
    name: str
    description: Optional[str] = None
    constituents: List[Dict] = Field(default_factory=list)


class PerformanceRatios(BaseModel):
    portfolio_node_id: str
    period_start: date
    period_end: date
    sharpe_ratio: Optional[float] = None
    information_ratio: Optional[float] = None
    tracking_error: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
