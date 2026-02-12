"""JWT authentication middleware for FastAPI services.

Stub implementation - replace with actual JWT validation in production.
"""
from __future__ import annotations

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware.

    Currently a pass-through stub. In production, this will:
    1. Extract Bearer token from Authorization header
    2. Validate JWT signature and expiry
    3. Attach user identity to request state
    """

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Stub: allow all requests, attach default identity
        request.state.user_id = "system"
        request.state.tenant_id = "INTERNAL"

        return await call_next(request)
