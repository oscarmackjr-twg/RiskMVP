"""Reusable health check endpoint with optional DB connectivity verification."""
from __future__ import annotations

from fastapi import FastAPI


def add_health_endpoint(app: FastAPI) -> None:
    """Add a /health endpoint to the given FastAPI app."""

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/health/deep")
    def deep_health():
        """Health check that verifies DB connectivity."""
        try:
            from services.common.db import db_conn
            with db_conn() as conn:
                conn.execute("SELECT 1")
            return {"ok": True, "db": "connected"}
        except Exception as e:
            return {"ok": False, "db": str(e)}
