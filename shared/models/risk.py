"""Risk analytics domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class RiskMeasure(str, Enum):
    PV = "PV"
    DV01 = "DV01"
    DURATION = "DURATION"
    CONVEXITY = "CONVEXITY"
    FX_DELTA = "FX_DELTA"
    VAR_95 = "VAR_95"
    VAR_99 = "VAR_99"
    EXPECTED_SHORTFALL = "EXPECTED_SHORTFALL"
    SPREAD_DURATION = "SPREAD_DURATION"
    KEY_RATE_DURATION = "KEY_RATE_DURATION"


class VaRMethod(str, Enum):
    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"
    MONTE_CARLO = "MONTE_CARLO"


class RiskResult(BaseModel):
    run_id: str
    position_id: str
    scenario_id: str
    measures: Dict[str, float] = Field(default_factory=dict)
    compute_meta: Dict[str, Any] = Field(default_factory=dict)


class VaRResult(BaseModel):
    portfolio_node_id: str
    as_of_date: datetime
    method: VaRMethod
    confidence_level: float  # 0.95, 0.99
    holding_period_days: int = 1
    var_amount: float
    expected_shortfall: Optional[float] = None
    component_var: Dict[str, float] = Field(default_factory=dict)


class DurationResult(BaseModel):
    position_id: str
    macaulay_duration: Optional[float] = None
    modified_duration: Optional[float] = None
    effective_duration: Optional[float] = None
    convexity: Optional[float] = None
    key_rate_durations: Dict[str, float] = Field(default_factory=dict)


class CreditAssessment(BaseModel):
    position_id: str
    instrument_id: str
    pd: Optional[float] = None  # Probability of default
    lgd: Optional[float] = None  # Loss given default
    ead: Optional[float] = None  # Exposure at default
    expected_loss: Optional[float] = None
    unexpected_loss: Optional[float] = None
    rating: Optional[str] = None
