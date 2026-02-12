"""Instrument domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from enum import Enum

from shared.models.common import Currency, DayCount, Rating


class InstrumentType(str, Enum):
    FX_FWD = "FX_FWD"
    AMORT_LOAN = "AMORT_LOAN"
    FIXED_BOND = "FIXED_BOND"
    FLOATING_RATE = "FLOATING_RATE"
    CALLABLE_BOND = "CALLABLE_BOND"
    PUTABLE_BOND = "PUTABLE_BOND"
    ABS_MBS = "ABS_MBS"
    STRUCTURED = "STRUCTURED"
    DERIVATIVE = "DERIVATIVE"


class InstrumentStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"


class InstrumentBase(BaseModel):
    instrument_id: str
    instrument_type: InstrumentType
    issuer_id: Optional[str] = None
    sector: Optional[str] = None
    currency: Currency = Currency.USD


class InstrumentVersion(BaseModel):
    instrument_id: str
    version: int
    status: InstrumentStatus
    terms_json: Dict[str, Any]
    conventions_json: Dict[str, Any]
    underlyings_json: Optional[Dict[str, Any]] = None
    risk_modeling_json: Dict[str, Any]
    governance_json: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class TradeEvent(BaseModel):
    event_id: str
    instrument_id: str
    event_type: str  # BOOKING, AMENDMENT, TERMINATION
    event_date: date
    details_json: Dict[str, Any] = Field(default_factory=dict)


class Issuer(BaseModel):
    issuer_id: str
    name: str
    sector: Optional[str] = None
    country: Optional[str] = None
    rating: Optional[Rating] = None
