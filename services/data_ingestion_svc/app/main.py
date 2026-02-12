"""Data ingestion service -- market feeds, loan servicing, vendor integration, lineage, and history."""
from __future__ import annotations

from services.common.service_base import create_service_app

from services.data_ingestion_svc.app.routes.market_feeds import router as market_feeds_router
from services.data_ingestion_svc.app.routes.loan_servicing import router as loan_servicing_router
from services.data_ingestion_svc.app.routes.vendor import router as vendor_router
from services.data_ingestion_svc.app.routes.lineage import router as lineage_router
from services.data_ingestion_svc.app.routes.history import router as history_router

app = create_service_app(
    title="data-ingestion-svc",
    description="Market feeds, loan servicing, vendor integration, data lineage, and historical versioning",
)

app.include_router(market_feeds_router, prefix="/api/v1/ingestion/market-feeds", tags=["Market Feeds"])
app.include_router(loan_servicing_router, prefix="/api/v1/ingestion/loan-servicing", tags=["Loan Servicing"])
app.include_router(vendor_router, prefix="/api/v1/ingestion/vendors", tags=["Vendors"])
app.include_router(lineage_router, prefix="/api/v1/ingestion/lineage", tags=["Data Lineage"])
app.include_router(history_router, prefix="/api/v1/ingestion/history", tags=["History"])
