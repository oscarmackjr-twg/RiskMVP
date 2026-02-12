"""Regulatory and compliance domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum


class RegulatoryFramework(str, Enum):
    CECL = "CECL"
    IFRS9 = "IFRS9"
    BASEL_III = "BASEL_III"
    GAAP = "GAAP"


class CECLResult(BaseModel):
    result_id: str
    portfolio_node_id: str
    as_of_date: date
    lifetime_ecl: float
    twelve_month_ecl: float
    stage: int  # 1, 2, 3
    allowance: float
    parameters: Dict[str, Any] = Field(default_factory=dict)


class BaselCapital(BaseModel):
    result_id: str
    portfolio_node_id: str
    as_of_date: date
    rwa: float  # Risk-weighted assets
    tier1_capital: Optional[float] = None
    tier2_capital: Optional[float] = None
    total_capital_ratio: Optional[float] = None
    leverage_ratio: Optional[float] = None


class RWACalculation(BaseModel):
    position_id: str
    instrument_id: str
    exposure: float
    risk_weight: float
    rwa: float
    approach: str  # STANDARDIZED, FIRB, AIRB


class AccountingEntry(BaseModel):
    entry_id: str
    instrument_id: str
    framework: RegulatoryFramework
    classification: str  # AMORTIZED_COST, FVOCI, FVTPL
    carrying_value: float
    fair_value: Optional[float] = None
    unrealized_gl: Optional[float] = None
