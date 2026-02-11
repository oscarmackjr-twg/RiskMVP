"""Factory for creating FastAPI applications with common middleware and configuration."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.common.health import add_health_endpoint
from services.common.errors import add_error_handlers


def create_service_app(
    title: str,
    version: str = "0.1.0",
    description: str = "",
) -> FastAPI:
    """Create a FastAPI app with standard middleware, health endpoint, and error handlers.

    Usage in each service's main.py:
        from services.common.service_base import create_service_app
        app = create_service_app(title="instrument-svc")
    """
    app = FastAPI(title=title, version=version, description=description)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health endpoint
    add_health_endpoint(app)

    # Standard error handlers
    add_error_handlers(app)

    return app
