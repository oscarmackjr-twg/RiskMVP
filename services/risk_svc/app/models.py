"""Pydantic request/response models for the Risk Service."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Market Risk
# ---------------------------------------------------------------------------

class MarketRiskRequest(BaseModel):
    """Request body for market risk computation."""
    portfolio_id: str
    as_of_date: Optional[datetime] = None
    measures: List[Literal[
        "DURATION", "MODIFIED_DURATION", "DV01", "CONVEXITY",
        "VAR_95", "VAR_99", "ES_95", "ES_99",
        "BETA", "DELTA", "GAMMA", "VEGA"
    ]] = Field(default_factory=lambda: ["DV01", "VAR_95"])
    confidence_level: float = Field(0.95, ge=0.0, le=1.0)
    horizon_days: int = Field(1, ge=1, le=252)
    method: Literal["HISTORICAL", "PARAMETRIC", "MONTE_CARLO"] = "PARAMETRIC"


class MarketRiskMeasure(BaseModel):
    """A single computed market risk measure."""
    measure: str
    value: float
    unit: str = ""
    as_of_date: Optional[datetime] = None


class MarketRiskResponse(BaseModel):
    """Response for market risk computation."""
    portfolio_id: str
    as_of_date: Optional[datetime] = None
    method: str
    horizon_days: int
    measures: List[MarketRiskMeasure] = Field(default_factory=list)


class VaRBreakdown(BaseModel):
    """VaR contribution by risk factor or position."""
    key: str
    component_var: float
    marginal_var: float
    pct_contribution: float = 0.0


class VaRResponse(BaseModel):
    """Detailed VaR response with decomposition."""
    portfolio_id: str
    confidence_level: float
    horizon_days: int
    method: str
    portfolio_var: float
    diversification_benefit: float = 0.0
    breakdown: List[VaRBreakdown] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Credit Risk
# ---------------------------------------------------------------------------

class CreditRiskRequest(BaseModel):
    """Request body for credit risk computation."""
    portfolio_id: str
    as_of_date: Optional[datetime] = None
    measures: List[Literal[
        "PD", "LGD", "EAD", "EXPECTED_LOSS", "UNEXPECTED_LOSS",
        "CREDIT_VAR", "RAROC", "SPREAD_DURATION"
    ]] = Field(default_factory=lambda: ["EXPECTED_LOSS", "PD"])
    horizon_months: int = Field(12, ge=1, le=120)
    rating_model: Literal["INTERNAL", "MOODYS", "SP", "FITCH"] = "INTERNAL"


class CreditExposure(BaseModel):
    """Credit exposure for a single counterparty or issuer."""
    entity_id: str
    entity_name: Optional[str] = None
    rating: Optional[str] = None
    pd: float = 0.0
    lgd: float = 0.0
    ead: float = 0.0
    expected_loss: float = 0.0
    unexpected_loss: float = 0.0
    raroc: Optional[float] = None


class CreditRiskResponse(BaseModel):
    """Response for credit risk computation."""
    portfolio_id: str
    as_of_date: Optional[datetime] = None
    horizon_months: int
    total_ead: float = 0.0
    total_expected_loss: float = 0.0
    total_unexpected_loss: float = 0.0
    credit_var: Optional[float] = None
    exposures: List[CreditExposure] = Field(default_factory=list)


class RatingMigrationMatrix(BaseModel):
    """Credit rating migration/transition matrix."""
    from_rating: str
    to_rating: str
    probability: float


class CreditMigrationResponse(BaseModel):
    """Response for credit migration analysis."""
    portfolio_id: str
    horizon_months: int
    rating_model: str
    transitions: List[RatingMigrationMatrix] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Liquidity Risk
# ---------------------------------------------------------------------------

class LiquidityRiskRequest(BaseModel):
    """Request body for liquidity risk assessment."""
    portfolio_id: str
    as_of_date: Optional[datetime] = None
    horizon_days: int = Field(5, ge=1, le=252, description="Liquidation horizon in business days")
    market_stress: Literal["NORMAL", "STRESSED", "SEVERE"] = "NORMAL"


class LiquidityBucket(BaseModel):
    """Liquidity profile for a time bucket."""
    bucket_label: str = Field(..., description="e.g. '0-1D', '1-7D', '7-30D', '30D+'")
    market_value: float = 0.0
    pct_of_portfolio: float = 0.0
    estimated_liquidation_cost_bps: float = 0.0


class LiquidityRiskResponse(BaseModel):
    """Response for liquidity risk assessment."""
    portfolio_id: str
    as_of_date: Optional[datetime] = None
    market_stress: str
    weighted_avg_bid_ask_bps: float = 0.0
    weighted_avg_time_to_liquidate_days: float = 0.0
    lcr: Optional[float] = Field(None, description="Liquidity Coverage Ratio")
    nsfr: Optional[float] = Field(None, description="Net Stable Funding Ratio")
    liquidity_buckets: List[LiquidityBucket] = Field(default_factory=list)


class LiquidityScoreOut(BaseModel):
    """Liquidity score for a single position."""
    position_id: str
    instrument_id: str
    bid_ask_spread_bps: float = 0.0
    avg_daily_volume: Optional[float] = None
    days_to_liquidate: float = 0.0
    liquidity_score: float = Field(0.0, ge=0.0, le=100.0, description="0=illiquid, 100=highly liquid")


# ---------------------------------------------------------------------------
# Concentration Risk
# ---------------------------------------------------------------------------

class ConcentrationRequest(BaseModel):
    """Request body for concentration risk analysis."""
    portfolio_id: str
    dimension: Literal["issuer", "sector", "geography", "rating", "currency", "counterparty"]
    as_of_date: Optional[datetime] = None
    limit_pct: Optional[float] = Field(None, description="Alert threshold as pct of portfolio")


class ConcentrationBucket(BaseModel):
    """Concentration for a single entity in a dimension."""
    key: str
    exposure: float
    weight_pct: float
    limit_pct: Optional[float] = None
    breach: bool = False


class ConcentrationResponse(BaseModel):
    """Response for concentration risk analysis."""
    portfolio_id: str
    dimension: str
    as_of_date: Optional[datetime] = None
    hhi: float = Field(0.0, description="Herfindahl-Hirschman Index (0-10000)")
    top_n_pct: float = Field(0.0, description="Weight of top-N entities")
    buckets: List[ConcentrationBucket] = Field(default_factory=list)
    breaches: List[ConcentrationBucket] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sensitivities
# ---------------------------------------------------------------------------

class SensitivityRequest(BaseModel):
    """Request body for sensitivity / key-rate analysis."""
    portfolio_id: str
    as_of_date: Optional[datetime] = None
    sensitivity_type: Literal[
        "KEY_RATE_DURATION", "SPREAD_DURATION", "FX_SENSITIVITY",
        "EQUITY_SENSITIVITY", "THETA", "CROSS_GAMMA"
    ] = "KEY_RATE_DURATION"
    shock_size_bps: float = Field(1.0, description="Shock size in basis points")
    tenors: Optional[List[str]] = Field(
        None, description="Specific tenors for key-rate analysis, e.g. ['1Y','2Y','5Y','10Y','30Y']"
    )


class SensitivityBucket(BaseModel):
    """Sensitivity for a single tenor or risk factor."""
    factor: str = Field(..., description="Risk factor label (tenor, currency pair, etc.)")
    sensitivity: float = Field(..., description="Dollar sensitivity per 1bp shock")
    pct_of_total: float = 0.0


class SensitivityResponse(BaseModel):
    """Response for sensitivity analysis."""
    portfolio_id: str
    sensitivity_type: str
    shock_size_bps: float
    as_of_date: Optional[datetime] = None
    total_sensitivity: float = 0.0
    buckets: List[SensitivityBucket] = Field(default_factory=list)


class ScenarioAnalysisRequest(BaseModel):
    """Request body for ad-hoc scenario / stress test."""
    portfolio_id: str
    scenario_name: str
    shocks: Dict[str, float] = Field(
        ..., description="Map of risk factor to shock value, e.g. {'USD-OIS': 50, 'EUR/USD': -0.05}"
    )
    as_of_date: Optional[datetime] = None


class ScenarioAnalysisResponse(BaseModel):
    """Response for ad-hoc scenario analysis."""
    portfolio_id: str
    scenario_name: str
    base_pv: float = 0.0
    stressed_pv: float = 0.0
    pnl_impact: float = 0.0
    pnl_impact_pct: float = 0.0
    position_impacts: List[Dict[str, Any]] = Field(default_factory=list)
