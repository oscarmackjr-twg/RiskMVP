"""Risk Service - FastAPI application (Port 8006).

Provides market risk, credit risk, liquidity risk, concentration monitoring,
and sensitivity / key-rate analysis endpoints.
"""
from __future__ import annotations

from services.common.service_base import create_service_app

from services.risk_svc.app.routes.market_risk import router as market_risk_router
from services.risk_svc.app.routes.credit_risk import router as credit_risk_router
from services.risk_svc.app.routes.liquidity_risk import router as liquidity_risk_router
from services.risk_svc.app.routes.concentration import router as concentration_router
from services.risk_svc.app.routes.sensitivities import router as sensitivities_router

app = create_service_app(
    title="risk-svc",
    description="Risk analytics: market risk, credit risk, liquidity risk, concentration, and sensitivities",
)

app.include_router(market_risk_router, prefix="/api/v1/risk/market", tags=["market-risk"])
app.include_router(credit_risk_router, prefix="/api/v1/risk/credit", tags=["credit-risk"])
app.include_router(liquidity_risk_router, prefix="/api/v1/risk/liquidity", tags=["liquidity-risk"])
app.include_router(concentration_router, prefix="/api/v1/risk/concentration", tags=["concentration"])
app.include_router(sensitivities_router, prefix="/api/v1/risk/sensitivities", tags=["sensitivities"])
