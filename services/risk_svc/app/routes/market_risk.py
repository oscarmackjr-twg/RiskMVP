"""Market risk endpoints - Duration, DV01, Convexity, VaR, Expected Shortfall."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.risk_svc.app.models import (
    MarketRiskRequest,
    MarketRiskResponse,
    VaRResponse,
)

router = APIRouter()


@router.post("/compute", response_model=MarketRiskResponse)
def compute_market_risk(req: MarketRiskRequest):
    """Compute market risk measures (DV01, duration, convexity, VaR, ES) for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/summary", response_model=MarketRiskResponse)
def get_market_risk_summary(
    portfolio_id: str,
    as_of_date: Optional[str] = Query(None),
):
    """Get cached market risk summary for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/dv01")
def get_dv01(portfolio_id: str):
    """Get DV01 (dollar value of a basis point) for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/duration")
def get_duration(portfolio_id: str):
    """Get effective and modified duration for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/convexity")
def get_convexity(portfolio_id: str):
    """Get convexity for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/var", response_model=VaRResponse)
def compute_var(req: MarketRiskRequest):
    """Compute Value-at-Risk with decomposition by risk factor."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/var-history")
def get_var_history(
    portfolio_id: str,
    confidence_level: float = Query(0.95),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Get historical VaR time-series for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/expected-shortfall")
def get_expected_shortfall(
    portfolio_id: str,
    confidence_level: float = Query(0.95),
    horizon_days: int = Query(1),
):
    """Get Expected Shortfall (CVaR) for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/greeks")
def get_greeks(portfolio_id: str):
    """Get portfolio-level Greeks (delta, gamma, vega, theta)."""
    raise HTTPException(status_code=501, detail="Not implemented")
