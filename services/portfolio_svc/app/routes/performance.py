"""Performance measurement, total return, attribution, and benchmark endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.portfolio_svc.app.models import (
    AttributionResponse,
    PerformanceRequest,
    PerformanceSummary,
)

router = APIRouter()


@router.post("/compute", response_model=PerformanceSummary)
def compute_performance(req: PerformanceRequest):
    """Compute total return and risk-adjusted performance metrics."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/summary", response_model=PerformanceSummary)
def get_performance_summary(
    portfolio_id: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """Get cached performance summary for a portfolio over a date range."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/total-return")
def get_total_return(
    portfolio_id: str,
    start_date: str = Query(...),
    end_date: str = Query(...),
    frequency: str = Query("DAILY"),
):
    """Get time-weighted total return series."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/attribution", response_model=AttributionResponse)
def compute_attribution(req: PerformanceRequest):
    """Compute Brinson-style performance attribution vs. benchmark."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/attribution/by-sector", response_model=AttributionResponse)
def get_attribution_by_sector(
    portfolio_id: str,
    benchmark_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """Get performance attribution grouped by sector."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/attribution/by-geography", response_model=AttributionResponse)
def get_attribution_by_geography(
    portfolio_id: str,
    benchmark_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """Get performance attribution grouped by geography."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/drawdown")
def get_drawdown_series(
    portfolio_id: str,
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """Get drawdown time-series for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/benchmark-comparison")
def compare_to_benchmark(
    portfolio_id: str,
    benchmark_id: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    """Compare portfolio performance to a benchmark index."""
    raise HTTPException(status_code=501, detail="Not implemented")
