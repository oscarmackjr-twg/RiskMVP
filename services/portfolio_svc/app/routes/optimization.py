"""Rebalancing recommendations and portfolio optimization endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from services.portfolio_svc.app.models import (
    OptimizationRequest,
    OptimizationResponse,
    RebalanceTrade,
)

router = APIRouter()


@router.post("/optimize", response_model=OptimizationResponse)
def optimize_portfolio(req: OptimizationRequest):
    """Run portfolio optimization and return recommended trades."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/rebalance", response_model=OptimizationResponse)
def rebalance_portfolio(req: OptimizationRequest):
    """Generate rebalancing trades to bring portfolio back to target weights."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/current-weights")
def get_current_weights(portfolio_id: str):
    """Get current portfolio weights by position."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/target-weights")
def get_target_weights(portfolio_id: str):
    """Get target (model) portfolio weights."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.put("/{portfolio_id}/target-weights")
def set_target_weights(portfolio_id: str, weights: List[dict]):
    """Set target weights for a portfolio (for rebalancing)."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/drift")
def get_portfolio_drift(portfolio_id: str):
    """Get drift analysis showing deviation from target weights."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{portfolio_id}/what-if")
def what_if_trade(
    portfolio_id: str,
    instrument_id: str = Query(...),
    trade_quantity: float = Query(...),
):
    """Simulate the impact of a proposed trade on portfolio weights and risk."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/efficient-frontier")
def get_efficient_frontier(
    portfolio_id: str,
    num_points: int = Query(20, ge=5, le=100),
):
    """Compute the efficient frontier for the portfolio's current holdings."""
    raise HTTPException(status_code=501, detail="Not implemented")
