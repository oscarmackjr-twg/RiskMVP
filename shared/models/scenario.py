"""Scenario and stress testing domain models."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ScenarioType(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    STOCHASTIC = "STOCHASTIC"
    HISTORICAL = "HISTORICAL"
    HYPOTHETICAL = "HYPOTHETICAL"


class ShockType(str, Enum):
    PARALLEL = "PARALLEL"
    TWIST = "TWIST"
    BUTTERFLY = "BUTTERFLY"
    KEY_RATE = "KEY_RATE"
    FX_SPOT = "FX_SPOT"
    CREDIT_SPREAD = "CREDIT_SPREAD"


class ScenarioDefinition(BaseModel):
    scenario_id: str
    name: str
    scenario_type: ScenarioType
    description: Optional[str] = None
    shocks: List[Dict[str, Any]] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class StressTest(BaseModel):
    stress_test_id: str
    name: str
    scenarios: List[str] = Field(default_factory=list)  # scenario_ids
    description: Optional[str] = None


class MonteCarloConfig(BaseModel):
    mc_id: str
    num_paths: int = 10000
    time_horizon_days: int = 252
    time_steps: int = 252
    seed: Optional[int] = None
    correlation_matrix_id: Optional[str] = None
    rate_model: str = "VASICEK"  # VASICEK, CIR, HW1F
    parameters: Dict[str, Any] = Field(default_factory=dict)
