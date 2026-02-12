"""Pydantic models for the regulatory / compliance service domain."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# CECL / Expected Credit Loss
# ---------------------------------------------------------------------------

class CECLSegment(BaseModel):
    """One segment in a CECL computation (e.g. a product-type or rating bucket)."""
    segment_id: str
    segment_name: str
    outstanding_balance: float
    expected_loss_rate: float
    expected_credit_loss: float
    qualitative_adjustment: float = 0.0


class CECLRequest(BaseModel):
    """Request to compute CECL reserves for a portfolio."""
    run_id: str
    as_of_date: datetime
    portfolio_node_id: str
    methodology: Literal["WARM", "DCF", "PD_LGD", "VINTAGE"] = "PD_LGD"
    forecast_scenario: Literal["BASE", "ADVERSE", "SEVERELY_ADVERSE"] = "BASE"
    qualitative_factors: Dict[str, float] = Field(default_factory=dict)


class CECLResult(BaseModel):
    """Result of a CECL computation."""
    run_id: str
    as_of_date: datetime
    portfolio_node_id: str
    methodology: str
    forecast_scenario: str
    segments: List[CECLSegment] = Field(default_factory=list)
    total_outstanding: float = 0.0
    total_ecl: float = 0.0
    reserve_rate_pct: float = 0.0
    computed_at: Optional[datetime] = None


class CECLHistoryEntry(BaseModel):
    """A single point in the CECL reserve history."""
    as_of_date: datetime
    total_ecl: float
    reserve_rate_pct: float
    methodology: str


# ---------------------------------------------------------------------------
# Basel III / Capital Analytics
# ---------------------------------------------------------------------------

class RWAExposure(BaseModel):
    """Risk-weighted asset exposure for a single position or bucket."""
    exposure_id: str
    asset_class: Literal[
        "CORPORATE", "SOVEREIGN", "BANK", "RETAIL", "EQUITY",
        "SECURITISATION", "OTHER",
    ]
    exposure_amount: float
    risk_weight_pct: float
    rwa: float
    pd: Optional[float] = None
    lgd: Optional[float] = None
    ead: Optional[float] = None


class BaselCapitalRequest(BaseModel):
    """Request to compute Basel III capital requirements."""
    run_id: str
    as_of_date: datetime
    portfolio_node_id: str
    approach: Literal["STANDARDISED", "F_IRB", "A_IRB"] = "STANDARDISED"


class BaselCapitalResult(BaseModel):
    """Result of a Basel III capital computation."""
    run_id: str
    as_of_date: datetime
    portfolio_node_id: str
    approach: str
    exposures: List[RWAExposure] = Field(default_factory=list)
    total_rwa: float = 0.0
    cet1_ratio_pct: Optional[float] = None
    tier1_ratio_pct: Optional[float] = None
    total_capital_ratio_pct: Optional[float] = None
    leverage_ratio_pct: Optional[float] = None
    computed_at: Optional[datetime] = None


class CapitalSummary(BaseModel):
    """High-level capital adequacy summary."""
    as_of_date: datetime
    total_rwa: float
    cet1_capital: float
    cet1_ratio_pct: float
    tier1_capital: float
    tier1_ratio_pct: float
    total_capital: float
    total_capital_ratio_pct: float
    buffer_requirement_pct: float
    surplus_deficit: float


# ---------------------------------------------------------------------------
# Accounting / GAAP / IFRS
# ---------------------------------------------------------------------------

class AccountingValuationRequest(BaseModel):
    """Request for GAAP/IFRS valuation classification."""
    run_id: str
    as_of_date: datetime
    portfolio_node_id: str
    standard: Literal["US_GAAP", "IFRS9"] = "US_GAAP"


class FairValueEntry(BaseModel):
    """A single instrument's fair-value classification."""
    position_id: str
    instrument_id: str
    classification: Literal[
        "LEVEL_1", "LEVEL_2", "LEVEL_3",   # Fair-value hierarchy
        "AMORTISED_COST", "FVTPL", "FVOCI", # IFRS 9 categories
        "HTM", "AFS", "HFT",               # Legacy US GAAP buckets
    ]
    carrying_value: float
    fair_value: float
    unrealised_pnl: float = 0.0


class AccountingValuationResult(BaseModel):
    """Result of an accounting valuation run."""
    run_id: str
    as_of_date: datetime
    standard: str
    entries: List[FairValueEntry] = Field(default_factory=list)
    total_carrying_value: float = 0.0
    total_fair_value: float = 0.0
    total_unrealised_pnl: float = 0.0
    computed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Audit Trail / Explainability
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    """A single audit trail event."""
    event_id: str
    timestamp: datetime
    actor: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, str] = Field(default_factory=dict)
    ip_address: Optional[str] = None


class AuditQuery(BaseModel):
    """Parameters for querying the audit log."""
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    actor: Optional[str] = None
    action: Optional[str] = None
    from_ts: Optional[datetime] = None
    to_ts: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = 0


class ExplainabilityRequest(BaseModel):
    """Request to explain a specific valuation result."""
    run_id: str
    position_id: str
    measure: str
    scenario_id: str = "BASE"


class ExplainabilityResult(BaseModel):
    """Explanation of how a valuation result was derived."""
    run_id: str
    position_id: str
    measure: str
    scenario_id: str
    computed_value: float
    inputs: Dict[str, str] = Field(default_factory=dict)
    methodology: str = ""
    steps: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Regulatory Reports
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    """Request to generate a regulatory report."""
    report_type: Literal[
        "CALL_REPORT", "FR_Y14", "CCAR", "DFAST",
        "CECL_DISCLOSURE", "PILLAR3", "LCR", "NSFR",
    ]
    as_of_date: datetime
    portfolio_node_id: str
    format: Literal["JSON", "CSV", "XBRL"] = "JSON"
    parameters: Dict[str, str] = Field(default_factory=dict)


class ReportStatus(BaseModel):
    """Status of a report generation job."""
    report_id: str
    report_type: str
    status: Literal["QUEUED", "GENERATING", "COMPLETED", "FAILED"]
    as_of_date: datetime
    requested_at: datetime
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    error_detail: Optional[str] = None


class ReportListItem(BaseModel):
    """Summary entry in a list of generated reports."""
    report_id: str
    report_type: str
    as_of_date: datetime
    status: str
    requested_at: datetime
