"""Sensitivity analysis endpoints - key rate duration, spread duration, etc."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.risk_svc.app.models import (
    ScenarioAnalysisRequest,
    ScenarioAnalysisResponse,
    SensitivityRequest,
    SensitivityResponse,
)

router = APIRouter()


@router.post("/compute", response_model=SensitivityResponse)
def compute_sensitivities(req: SensitivityRequest):
    """Compute sensitivity profile for a portfolio by risk factor."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/key-rate-duration", response_model=SensitivityResponse)
def get_key_rate_duration(
    portfolio_id: str,
    shock_size_bps: float = Query(1.0),
):
    """Get key-rate duration profile across standard tenors."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/spread-duration", response_model=SensitivityResponse)
def get_spread_duration(
    portfolio_id: str,
    shock_size_bps: float = Query(1.0),
):
    """Get spread duration (credit spread sensitivity) profile."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/fx-sensitivity", response_model=SensitivityResponse)
def get_fx_sensitivity(portfolio_id: str):
    """Get FX sensitivity (delta per currency pair)."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/equity-sensitivity", response_model=SensitivityResponse)
def get_equity_sensitivity(portfolio_id: str):
    """Get equity sensitivity (beta, delta by sector/index)."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/theta")
def get_theta(portfolio_id: str):
    """Get portfolio theta (time decay sensitivity)."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/cross-gamma")
def get_cross_gamma(portfolio_id: str):
    """Get cross-gamma (second-order cross-sensitivities)."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/scenario", response_model=ScenarioAnalysisResponse)
def run_scenario_analysis(req: ScenarioAnalysisRequest):
    """Run an ad-hoc scenario / stress test with custom shocks."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/stress-tests")
def list_stress_tests(portfolio_id: str):
    """List available predefined stress test scenarios."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{portfolio_id}/stress-tests/{scenario_name}")
def run_stress_test(portfolio_id: str, scenario_name: str):
    """Run a predefined stress test scenario against the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")
