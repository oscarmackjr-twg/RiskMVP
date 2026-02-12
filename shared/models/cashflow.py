"""Cash flow domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List
from enum import Enum


class CashFlowType(str, Enum):
    INTEREST = "INTEREST"
    PRINCIPAL = "PRINCIPAL"
    FEE = "FEE"
    PREPAYMENT = "PREPAYMENT"
    DEFAULT_RECOVERY = "DEFAULT_RECOVERY"


class CashFlow(BaseModel):
    pay_date: date
    cf_type: CashFlowType
    amount: float
    currency: str = "USD"
    discount_factor: Optional[float] = None
    present_value: Optional[float] = None


class AmortSchedule(BaseModel):
    instrument_id: str
    schedule_type: str  # LEVEL_PAY, BULLET, CUSTOM
    payment_frequency: str  # MONTHLY, QUARTERLY, SEMI_ANNUAL, ANNUAL
    flows: List[CashFlow] = Field(default_factory=list)
    total_principal: float = 0.0
    total_interest: float = 0.0


class PrepaymentAssumption(BaseModel):
    model_type: str  # CPR, PSA, CUSTOM
    rate: float  # e.g. CPR 10%
    parameters: dict = Field(default_factory=dict)


class WaterfallDefinition(BaseModel):
    waterfall_id: str
    deal_id: str
    tranches: List[dict] = Field(default_factory=list)
    rules: List[dict] = Field(default_factory=list)
