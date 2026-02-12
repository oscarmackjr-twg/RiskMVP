"""Regulatory service -- CECL, Basel III, GAAP/IFRS, capital analytics, audit, and reports."""
from __future__ import annotations

from services.common.service_base import create_service_app

from services.regulatory_svc.app.routes.cecl import router as cecl_router
from services.regulatory_svc.app.routes.basel import router as basel_router
from services.regulatory_svc.app.routes.accounting import router as accounting_router
from services.regulatory_svc.app.routes.audit import router as audit_router
from services.regulatory_svc.app.routes.model_governance import router as model_governance_router
from services.regulatory_svc.app.routes.reports import router as reports_router
from services.regulatory_svc.app.routes.alerts import router as alerts_router

app = create_service_app(
    title="regulatory-svc",
    description="CECL, Basel III, GAAP/IFRS, capital analytics, audit trail, model governance, and regulatory reports",
)

app.include_router(cecl_router, prefix="/api/v1/regulatory/cecl", tags=["CECL"])
app.include_router(basel_router, prefix="/api/v1/regulatory/basel", tags=["Basel III"])
app.include_router(accounting_router, prefix="/api/v1/regulatory/accounting", tags=["Accounting"])
app.include_router(audit_router, prefix="/api/v1/regulatory/audit", tags=["Audit"])
app.include_router(model_governance_router, prefix="/api/v1/regulatory/models", tags=["Model Governance"])
app.include_router(reports_router, prefix="/api/v1/regulatory/reports", tags=["Reports"])
app.include_router(alerts_router, prefix="/api/v1/regulatory/alerts", tags=["Alerts"])
