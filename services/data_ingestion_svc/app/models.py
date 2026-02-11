"""Pydantic models for the data ingestion service domain."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Market Feeds (yield curves, credit spreads, ratings)
# ---------------------------------------------------------------------------

class YieldCurveNode(BaseModel):
    """A single tenor point on a yield curve."""
    tenor: str
    rate: float


class YieldCurveUpload(BaseModel):
    """Request to ingest a yield curve."""
    curve_id: str
    curve_type: Literal["DISCOUNT", "FORECAST", "BASIS", "SPREAD"]
    currency: str
    as_of_date: datetime
    source: str
    nodes: List[YieldCurveNode]


class CreditSpreadUpload(BaseModel):
    """Request to ingest a credit spread curve."""
    issuer_id: str
    rating: str
    sector: str
    currency: str
    as_of_date: datetime
    source: str
    spreads: List[YieldCurveNode]


class RatingChange(BaseModel):
    """A single rating transition event."""
    entity_id: str
    agency: Literal["SP", "MOODYS", "FITCH", "DBRS"]
    rating: str
    outlook: Optional[str] = None
    as_of_date: datetime
    effective_date: datetime
    source: str


class FXSpotPair(BaseModel):
    """A single FX spot rate pair."""
    pair: str
    spot_rate: float


class FXSpotUpload(BaseModel):
    """Request to ingest FX spot rates for a market snapshot."""
    snapshot_id: str
    as_of_date: datetime
    source: str
    spots: List[FXSpotPair]


class FXSpotOut(BaseModel):
    """FX spot rate output."""
    pair: str
    snapshot_id: str
    spot_rate: float
    as_of_date: datetime
    source: str


class FXSpotStatus(BaseModel):
    """Status of FX spot ingestion."""
    snapshot_id: str
    pair_count: int
    ingested_at: datetime


class YieldCurveOut(BaseModel):
    """Yield curve output."""
    curve_id: str
    curve_type: str
    currency: str
    as_of_date: datetime
    source: str
    nodes: List[YieldCurveNode]


class CreditSpreadOut(BaseModel):
    """Credit spread output."""
    issuer_id: str
    rating: str
    sector: str
    currency: str
    as_of_date: datetime
    source: str
    spreads: List[YieldCurveNode]


class RatingHistoryOut(BaseModel):
    """Rating history output."""
    entity_id: str
    agency: str
    rating: str
    outlook: Optional[str]
    as_of_date: datetime
    effective_date: datetime


class MarketFeedStatus(BaseModel):
    """Status of a market feed ingestion job."""
    feed_id: str
    feed_type: str
    status: Literal["PASS", "FAIL", "PENDING"]
    record_count: int = 0
    ingested_at: datetime
    errors: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Loan Servicing Data
# ---------------------------------------------------------------------------

class PositionUpload(BaseModel):
    """A single position for batch upload."""
    instrument_id: str
    portfolio_node_id: str
    quantity: float
    base_ccy: str
    cost_basis: float
    book_value: float


class LoanServicingBatch(BaseModel):
    """Batch upload of loan servicing positions."""
    source_file: str
    as_of_date: datetime
    positions: List[PositionUpload]


class IngestionBatchStatus(BaseModel):
    """Status of a loan servicing batch ingestion."""
    batch_id: str
    status: Literal["COMPLETED", "FAILED"]
    record_count: int
    validation_errors: List[str] = Field(default_factory=list)
    ingested_at: datetime


class ReconcileRequest(BaseModel):
    """Request to reconcile positions against expected values."""
    portfolio_node_id: str
    as_of_date: datetime
    expected_positions: List[PositionUpload]


class ReconcileResponse(BaseModel):
    """Response from position reconciliation."""
    missing: List[str] = Field(default_factory=list)
    extra: List[str] = Field(default_factory=list)
    mismatches: List[Dict[str, Any]] = Field(default_factory=list)
    match_count: int
    total_count: int


# ---------------------------------------------------------------------------
# Vendor Integration
# ---------------------------------------------------------------------------

class VendorConfig(BaseModel):
    """Configuration for a pricing data vendor."""
    vendor_id: str
    vendor_name: str
    vendor_type: Literal["MARKET_DATA", "PRICING", "REFERENCE_DATA", "RATINGS"]
    connection_type: Literal["API", "SFTP", "FILE_DROP", "STREAMING"]
    endpoint_url: Optional[str] = None
    schedule_cron: Optional[str] = None
    enabled: bool = True
    parameters: Dict[str, str] = Field(default_factory=dict)


class VendorConfigOut(BaseModel):
    """Vendor config response including system fields."""
    vendor_id: str
    vendor_name: str
    vendor_type: str
    connection_type: str
    endpoint_url: Optional[str] = None
    schedule_cron: Optional[str] = None
    enabled: bool
    created_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None


class VendorSyncRequest(BaseModel):
    """Request to trigger a vendor data sync."""
    vendor_id: str
    sync_type: Literal["FULL", "INCREMENTAL"] = "INCREMENTAL"
    as_of_date: Optional[datetime] = None


class VendorSyncStatus(BaseModel):
    """Status of a vendor sync job."""
    sync_id: str
    vendor_id: str
    sync_type: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "FAILED"]
    records_fetched: int = 0
    records_stored: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Data Lineage
# ---------------------------------------------------------------------------

class LineageNode(BaseModel):
    """A single node in the data lineage graph."""
    node_id: str
    node_type: Literal["SOURCE", "TRANSFORM", "STORE", "OUTPUT"]
    label: str
    system: str
    metadata: Dict[str, str] = Field(default_factory=dict)


class LineageEdge(BaseModel):
    """An edge connecting two lineage nodes."""
    source_node_id: str
    target_node_id: str
    relationship: Literal["DERIVES_FROM", "FEEDS_INTO", "TRANSFORMS", "VALIDATES"]
    metadata: Dict[str, str] = Field(default_factory=dict)


class LineageRecord(BaseModel):
    """A data lineage record tracking where data came from."""
    lineage_id: str
    data_type: str
    resource_id: str
    source_system: str
    source_identifier: str
    ingested_at: datetime
    transformation_chain: List[str] = Field(default_factory=list)
    quality_checks_passed: bool = True
    metadata: Dict[str, str] = Field(default_factory=dict)


class LineageOut(BaseModel):
    """Lineage output."""
    lineage_id: str
    feed_type: str
    feed_id: Optional[str]
    source_system: str
    source_identifier: str
    ingested_at: datetime
    transformation_chain: List[str]
    quality_checks_passed: bool
    metadata_json: Optional[Dict[str, Any]] = None


class LineageGraph(BaseModel):
    """Full lineage graph for a resource."""
    resource_id: str
    nodes: List[LineageNode] = Field(default_factory=list)
    edges: List[LineageEdge] = Field(default_factory=list)


class LineageGraphOut(BaseModel):
    """Lineage graph response."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class ImpactAnalysisRequest(BaseModel):
    """Request for impact analysis."""
    feed_id: str


class ImpactAnalysisResponse(BaseModel):
    """Response from impact analysis."""
    affected_runs: List[str] = Field(default_factory=list)
    affected_positions: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Historical Data / Versioning
# ---------------------------------------------------------------------------

class DataVersion(BaseModel):
    """A versioned snapshot of an ingested dataset."""
    version_id: str
    dataset_id: str
    dataset_type: Literal[
        "YIELD_CURVE", "CREDIT_SPREAD", "RATING",
        "LOAN_TAPE", "FX_SPOT", "REFERENCE_DATA",
    ]
    version_number: int
    as_of_date: datetime
    created_at: datetime
    record_count: int = 0
    checksum: Optional[str] = None
    is_current: bool = True


class DataVersionCompare(BaseModel):
    """Comparison result between two dataset versions."""
    dataset_id: str
    version_a: int
    version_b: int
    records_added: int = 0
    records_removed: int = 0
    records_modified: int = 0
    summary: str = ""


class HistoryQuery(BaseModel):
    """Parameters for querying historical data versions."""
    dataset_id: str
    dataset_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = Field(default=50, le=500)
    offset: int = 0


class DatasetSnapshotRequest(BaseModel):
    """Request to create a point-in-time snapshot of a dataset."""
    dataset_id: str
    dataset_type: str
    as_of_date: datetime
    label: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
