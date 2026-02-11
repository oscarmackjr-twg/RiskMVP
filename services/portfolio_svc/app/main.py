"""Portfolio Service - FastAPI application (Port 8005).

Manages portfolios, positions, aggregation, tagging, snapshots,
performance attribution, and optimization/rebalancing.
"""
from __future__ import annotations

from services.common.service_base import create_service_app

from services.portfolio_svc.app.routes.portfolios import router as portfolios_router
from services.portfolio_svc.app.routes.positions import router as positions_router
from services.portfolio_svc.app.routes.aggregation import router as aggregation_router
from services.portfolio_svc.app.routes.tags import router as tags_router
from services.portfolio_svc.app.routes.snapshots import router as snapshots_router
from services.portfolio_svc.app.routes.performance import router as performance_router
from services.portfolio_svc.app.routes.optimization import router as optimization_router
from services.portfolio_svc.app.routes.reference_data import router as reference_data_router
from services.portfolio_svc.app.routes.instruments import router as instruments_router

app = create_service_app(
    title="portfolio-svc",
    description="Portfolio management, positions, aggregation, performance, and optimization",
)

app.include_router(portfolios_router, prefix="/api/v1/portfolios", tags=["portfolios"])
app.include_router(positions_router, prefix="/api/v1/positions", tags=["positions"])
app.include_router(aggregation_router, prefix="/api/v1/aggregation", tags=["aggregation"])
app.include_router(tags_router, prefix="/api/v1/tags", tags=["tags"])
app.include_router(snapshots_router, prefix="/api/v1/snapshots", tags=["snapshots"])
app.include_router(performance_router, prefix="/api/v1/performance", tags=["performance"])
app.include_router(optimization_router, prefix="/api/v1/optimization", tags=["optimization"])
app.include_router(reference_data_router, prefix="/api/v1/reference-data", tags=["reference-data"])
app.include_router(instruments_router, prefix="/api/v1/instruments", tags=["instruments"])
