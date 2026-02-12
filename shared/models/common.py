"""Common enumerations and base types used across all services."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"


class DayCount(str, Enum):
    ACT_360 = "ACT/360"
    ACT_365 = "ACT/365"
    THIRTY_360 = "30/360"
    ACT_ACT = "ACT/ACT"


class Tenor(str, Enum):
    W1 = "1W"
    M1 = "1M"
    M3 = "3M"
    M6 = "6M"
    M9 = "9M"
    Y1 = "1Y"
    Y2 = "2Y"
    Y3 = "3Y"
    Y5 = "5Y"
    Y7 = "7Y"
    Y10 = "10Y"
    Y20 = "20Y"
    Y30 = "30Y"


class Rating(str, Enum):
    AAA = "AAA"
    AA_PLUS = "AA+"
    AA = "AA"
    AA_MINUS = "AA-"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    BBB_PLUS = "BBB+"
    BBB = "BBB"
    BBB_MINUS = "BBB-"
    BB_PLUS = "BB+"
    BB = "BB"
    BB_MINUS = "BB-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"
    NR = "NR"


class AuditMixin(BaseModel):
    """Mixin providing audit trail fields."""
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class PageRequest(BaseModel):
    """Standard pagination request."""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=1000)


class PageResponse(BaseModel):
    """Standard pagination response metadata."""
    offset: int
    limit: int
    total: int
    has_more: bool
