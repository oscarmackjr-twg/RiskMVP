"""Liquidity risk endpoints - bid/ask, time-to-liquidate, LCR."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from services.risk_svc.app.models import (
    LiquidityRiskRequest,
    LiquidityRiskResponse,
    LiquidityScoreOut,
)

router = APIRouter()


@router.post("/compute", response_model=LiquidityRiskResponse)
def compute_liquidity_risk(req: LiquidityRiskRequest):
    """Compute liquidity risk profile for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/summary", response_model=LiquidityRiskResponse)
def get_liquidity_risk_summary(
    portfolio_id: str,
    as_of_date: Optional[str] = Query(None),
):
    """Get cached liquidity risk summary for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/scores", response_model=List[LiquidityScoreOut])
def get_liquidity_scores(portfolio_id: str):
    """Get per-position liquidity scores for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/bid-ask-profile")
def get_bid_ask_profile(portfolio_id: str):
    """Get bid-ask spread profile across portfolio positions."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/time-to-liquidate")
def get_time_to_liquidate(
    portfolio_id: str,
    market_stress: str = Query("NORMAL", description="NORMAL, STRESSED, or SEVERE"),
):
    """Get estimated time-to-liquidate for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/lcr")
def get_lcr(portfolio_id: str):
    """Get Liquidity Coverage Ratio for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/nsfr")
def get_nsfr(portfolio_id: str):
    """Get Net Stable Funding Ratio for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/cash-flow-ladder")
def get_cash_flow_ladder(
    portfolio_id: str,
    horizon_days: int = Query(90, ge=1, le=365),
):
    """Get projected cash-flow ladder for liquidity planning."""
    raise HTTPException(status_code=501, detail="Not implemented")
