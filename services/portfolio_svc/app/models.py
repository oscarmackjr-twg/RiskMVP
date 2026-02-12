"""Pydantic request/response models for the Portfolio Service."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Portfolio hierarchy
# ---------------------------------------------------------------------------

class PortfolioCreate(BaseModel):
    """Request body to create a new portfolio node."""
    portfolio_id: str = Field(..., description="Unique portfolio identifier")
    name: str
    parent_id: Optional[str] = Field(None, description="Parent portfolio node for hierarchy")
    portfolio_type: Literal["FUND", "SLEEVE", "STRATEGY", "BOOK", "DESK"] = "FUND"
    currency: str = Field("USD", description="Base currency ISO code")
    inception_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PortfolioOut(BaseModel):
    """Response model for a single portfolio."""
    portfolio_id: str
    name: str
    parent_id: Optional[str] = None
    portfolio_type: str
    currency: str
    inception_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class PortfolioUpdate(BaseModel):
    """Partial update for a portfolio."""
    name: Optional[str] = None
    parent_id: Optional[str] = None
    portfolio_type: Optional[str] = None
    currency: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PortfolioTreeNode(BaseModel):
    """Recursive tree representation of portfolio hierarchy."""
    portfolio_id: str
    name: str
    portfolio_type: str
    children: List[PortfolioTreeNode] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Positions / Holdings
# ---------------------------------------------------------------------------

class PositionCreate(BaseModel):
    """Request body to add a position to a portfolio."""
    position_id: str
    portfolio_id: str
    instrument_id: str
    product_type: Literal["FX_FWD", "AMORT_LOAN", "FIXED_BOND", "EQUITY", "OPTION"]
    quantity: float
    cost_basis: Optional[float] = None
    currency: str = "USD"
    trade_date: Optional[datetime] = None
    settlement_date: Optional[datetime] = None
    counterparty: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PositionOut(BaseModel):
    """Response model for a single position."""
    position_id: str
    portfolio_id: str
    instrument_id: str
    product_type: str
    quantity: float
    cost_basis: Optional[float] = None
    currency: str
    trade_date: Optional[datetime] = None
    settlement_date: Optional[datetime] = None
    counterparty: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class PositionUpdate(BaseModel):
    """Partial update for a position."""
    quantity: Optional[float] = None
    cost_basis: Optional[float] = None
    counterparty: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

class AggregationRequest(BaseModel):
    """Request body for portfolio aggregation."""
    portfolio_id: str
    group_by: Literal["issuer", "sector", "rating", "geography", "currency", "product_type"]
    as_of_date: Optional[datetime] = None
    measure: str = Field("market_value", description="Measure to aggregate (market_value, notional, quantity)")


class AggregationBucket(BaseModel):
    """A single aggregation bucket."""
    key: str
    value: float
    weight_pct: float = Field(0.0, description="Percentage weight in portfolio")
    position_count: int = 0


class AggregationResponse(BaseModel):
    """Response for an aggregation query."""
    portfolio_id: str
    group_by: str
    measure: str
    total: float
    buckets: List[AggregationBucket] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tags / Segmentation
# ---------------------------------------------------------------------------

class TagAssignment(BaseModel):
    """Assign a tag to an entity (portfolio or position)."""
    entity_type: Literal["portfolio", "position"]
    entity_id: str
    tag_namespace: str = Field(..., description="Tag namespace, e.g. 'strategy', 'region'")
    tag_value: str


class TagOut(BaseModel):
    """Response model for a tag."""
    entity_type: str
    entity_id: str
    tag_namespace: str
    tag_value: str
    assigned_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Snapshots / Time-series
# ---------------------------------------------------------------------------

class SnapshotCreate(BaseModel):
    """Request body for taking a portfolio snapshot."""
    portfolio_node_id: str
    as_of_date: datetime
    include_hierarchy: bool = Field(False, description="Include child portfolios recursively")


class SnapshotOut(BaseModel):
    """Response model for a portfolio snapshot."""
    snapshot_id: str
    portfolio_node_id: str
    as_of_date: datetime
    total_positions: int = 0
    total_instruments: int = 0
    payload_json: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class SnapshotCompareRequest(BaseModel):
    """Request to compare two snapshots."""
    snapshot_id_1: str
    snapshot_id_2: str


class PositionChange(BaseModel):
    """Position change between snapshots."""
    instrument_id: str
    product_type: str
    base_ccy: str
    old_quantity: Optional[float] = None
    new_quantity: Optional[float] = None
    quantity_change: float


class SnapshotCompareResponse(BaseModel):
    """Response for snapshot comparison."""
    snapshot_id_1: str
    snapshot_id_2: str
    new_positions: List[Dict[str, Any]] = Field(default_factory=list)
    removed_positions: List[Dict[str, Any]] = Field(default_factory=list)
    quantity_changes: List[PositionChange] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class SnapshotTimeSeriesPoint(BaseModel):
    """A single point in snapshot time-series."""
    as_of_date: datetime
    position_count: int
    instrument_count: int


class PortfolioSnapshotCreate(BaseModel):
    """Request body for taking a portfolio snapshot."""
    portfolio_id: str
    as_of_date: datetime
    snapshot_type: Literal["EOD", "INTRADAY", "ADHOC"] = "EOD"


class PortfolioSnapshotOut(BaseModel):
    """Response model for a portfolio snapshot."""
    snapshot_id: str
    portfolio_id: str
    as_of_date: datetime
    snapshot_type: str
    position_count: int = 0
    total_market_value: Optional[float] = None
    created_at: Optional[datetime] = None


class TimeSeriesPoint(BaseModel):
    """A single point in a time-series."""
    date: datetime
    value: float


class TimeSeriesResponse(BaseModel):
    """Response for time-series query."""
    portfolio_id: str
    measure: str
    points: List[TimeSeriesPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Performance / Attribution
# ---------------------------------------------------------------------------

class PerformanceRequest(BaseModel):
    """Request body for performance computation."""
    portfolio_id: str
    start_date: datetime
    end_date: datetime
    benchmark_id: Optional[str] = None
    frequency: Literal["DAILY", "WEEKLY", "MONTHLY"] = "DAILY"


class PerformanceSummary(BaseModel):
    """Summary performance metrics."""
    portfolio_id: str
    start_date: datetime
    end_date: datetime
    total_return_pct: float = 0.0
    annualized_return_pct: float = 0.0
    volatility_pct: float = 0.0
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: float = 0.0
    benchmark_id: Optional[str] = None
    benchmark_return_pct: Optional[float] = None
    active_return_pct: Optional[float] = None
    tracking_error_pct: Optional[float] = None
    information_ratio: Optional[float] = None


class AttributionBucket(BaseModel):
    """Performance attribution by a grouping dimension."""
    key: str
    allocation_effect: float = 0.0
    selection_effect: float = 0.0
    interaction_effect: float = 0.0
    total_effect: float = 0.0


class AttributionResponse(BaseModel):
    """Response for performance attribution."""
    portfolio_id: str
    benchmark_id: str
    start_date: datetime
    end_date: datetime
    group_by: str
    buckets: List[AttributionBucket] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Optimization / Rebalancing
# ---------------------------------------------------------------------------

class OptimizationConstraint(BaseModel):
    """A constraint for portfolio optimization."""
    constraint_type: Literal["MAX_WEIGHT", "MIN_WEIGHT", "SECTOR_LIMIT", "TURNOVER_LIMIT", "TRACKING_ERROR"]
    target: Optional[str] = None
    value: float


class OptimizationRequest(BaseModel):
    """Request body for portfolio optimization / rebalancing."""
    portfolio_id: str
    objective: Literal["MIN_VARIANCE", "MAX_SHARPE", "MIN_TRACKING_ERROR", "RISK_PARITY"] = "MIN_VARIANCE"
    constraints: List[OptimizationConstraint] = Field(default_factory=list)
    benchmark_id: Optional[str] = None
    as_of_date: Optional[datetime] = None


class RebalanceTrade(BaseModel):
    """A recommended trade from the optimization."""
    instrument_id: str
    current_weight_pct: float
    target_weight_pct: float
    trade_direction: Literal["BUY", "SELL"]
    trade_quantity: float
    estimated_cost: float = 0.0


class OptimizationResponse(BaseModel):
    """Response for portfolio optimization."""
    portfolio_id: str
    objective: str
    status: Literal["OPTIMAL", "INFEASIBLE", "SUBOPTIMAL"] = "OPTIMAL"
    recommended_trades: List[RebalanceTrade] = Field(default_factory=list)
    expected_return_pct: Optional[float] = None
    expected_risk_pct: Optional[float] = None
    turnover_pct: float = 0.0
