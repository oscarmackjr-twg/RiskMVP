"""Credit risk endpoints - PD, LGD, EAD, expected loss, RAROC."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.risk_svc.app.models import (
    CreditMigrationResponse,
    CreditRiskRequest,
    CreditRiskResponse,
)

router = APIRouter()


@router.post("/compute", response_model=CreditRiskResponse)
def compute_credit_risk(req: CreditRiskRequest):
    """Compute credit risk measures (PD, LGD, EAD, expected/unexpected loss) for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/summary", response_model=CreditRiskResponse)
def get_credit_risk_summary(
    portfolio_id: str,
    as_of_date: Optional[str] = Query(None),
):
    """Get cached credit risk summary for a portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/expected-loss")
def get_expected_loss(portfolio_id: str):
    """Get total expected loss for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/exposures")
def get_credit_exposures(
    portfolio_id: str,
    group_by: str = Query("counterparty", description="Group by counterparty, issuer, or rating"),
):
    """Get credit exposure breakdown by counterparty, issuer, or rating."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/rating-distribution")
def get_rating_distribution(portfolio_id: str):
    """Get portfolio exposure distribution across credit ratings."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/migration", response_model=CreditMigrationResponse)
def compute_migration_analysis(req: CreditRiskRequest):
    """Compute credit rating migration/transition analysis."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/raroc")
def get_raroc(portfolio_id: str):
    """Get Risk-Adjusted Return on Capital for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/credit-var")
def get_credit_var(
    portfolio_id: str,
    confidence_level: float = Query(0.99),
    horizon_months: int = Query(12),
):
    """Get Credit VaR for the portfolio."""
    raise HTTPException(status_code=501, detail="Not implemented")
