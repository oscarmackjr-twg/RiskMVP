"""Aggregation endpoints - group by issuer, sector, rating, geography, etc."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.portfolio_svc.app.models import (
    AggregationRequest,
    AggregationResponse,
    AggregationBucket,
)
from services.common.db import db_conn
from services.common.portfolio_queries import (
    build_issuer_aggregation_query,
    build_sector_aggregation_query,
    build_rating_aggregation_query,
    build_geography_aggregation_query,
    build_currency_aggregation_query,
    build_product_type_aggregation_query,
)

router = APIRouter()


@router.post("", response_model=AggregationResponse)
def aggregate_portfolio(req: AggregationRequest):
    """Aggregate portfolio exposure by the requested dimension."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{portfolio_id}/by-issuer")
def aggregate_by_issuer(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for valuation data"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
):
    """Aggregate portfolio exposure grouped by issuer."""
    query, params = build_issuer_aggregation_query(portfolio_id, run_id, snapshot_id)

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return {
                "portfolio_id": portfolio_id,
                "group_by": "issuer",
                "measure": "market_value",
                "total": 0.0,
                "buckets": []
            }

        total = sum(row["pv_usd"] for row in rows)
        buckets = [
            {
                "key": f"{row['issuer_name']} ({row['issuer_id']})",
                "value": float(row["pv_usd"]),
                "weight_pct": float(row["weight_pct"]),
                "position_count": row["position_count"],
            }
            for row in rows
        ]

        return {
            "portfolio_id": portfolio_id,
            "group_by": "issuer",
            "measure": "market_value",
            "total": float(total),
            "buckets": buckets
        }


@router.get("/{portfolio_id}/by-sector")
def aggregate_by_sector(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for valuation data"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
):
    """Aggregate portfolio exposure grouped by sector."""
    query, params = build_sector_aggregation_query(portfolio_id, run_id, snapshot_id)

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return {
                "portfolio_id": portfolio_id,
                "group_by": "sector",
                "measure": "market_value",
                "total": 0.0,
                "buckets": []
            }

        total = sum(row["pv_usd"] for row in rows)
        buckets = [
            {
                "key": row["sector"],
                "value": float(row["pv_usd"]),
                "weight_pct": float(row["weight_pct"]),
                "position_count": row["position_count"],
            }
            for row in rows
        ]

        return {
            "portfolio_id": portfolio_id,
            "group_by": "sector",
            "measure": "market_value",
            "total": float(total),
            "buckets": buckets
        }


@router.get("/{portfolio_id}/by-rating")
def aggregate_by_rating(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for valuation data"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
):
    """Aggregate portfolio exposure grouped by credit rating."""
    query, params = build_rating_aggregation_query(portfolio_id, run_id, snapshot_id)

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return {
                "portfolio_id": portfolio_id,
                "group_by": "rating",
                "measure": "market_value",
                "total": 0.0,
                "buckets": []
            }

        total = sum(row["pv_usd"] for row in rows)
        buckets = [
            {
                "key": f"{row['rating']} ({row['agency']})",
                "value": float(row["pv_usd"]),
                "weight_pct": float(row["weight_pct"]),
                "position_count": row["position_count"],
            }
            for row in rows
        ]

        return {
            "portfolio_id": portfolio_id,
            "group_by": "rating",
            "measure": "market_value",
            "total": float(total),
            "buckets": buckets
        }


@router.get("/{portfolio_id}/by-geography")
def aggregate_by_geography(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for valuation data"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
):
    """Aggregate portfolio exposure grouped by geography/country."""
    query, params = build_geography_aggregation_query(portfolio_id, run_id, snapshot_id)

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return {
                "portfolio_id": portfolio_id,
                "group_by": "geography",
                "measure": "market_value",
                "total": 0.0,
                "buckets": []
            }

        total = sum(row["pv_usd"] for row in rows)
        buckets = [
            {
                "key": row["geography"],
                "value": float(row["pv_usd"]),
                "weight_pct": float(row["weight_pct"]),
                "position_count": row["position_count"],
            }
            for row in rows
        ]

        return {
            "portfolio_id": portfolio_id,
            "group_by": "geography",
            "measure": "market_value",
            "total": float(total),
            "buckets": buckets
        }


@router.get("/{portfolio_id}/by-currency")
def aggregate_by_currency(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for valuation data"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
):
    """Aggregate portfolio exposure grouped by currency."""
    query, params = build_currency_aggregation_query(portfolio_id, run_id, snapshot_id)

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return {
                "portfolio_id": portfolio_id,
                "group_by": "currency",
                "measure": "market_value",
                "total": 0.0,
                "buckets": []
            }

        total = sum(row["pv_usd"] for row in rows)
        buckets = [
            {
                "key": row["currency"],
                "value": float(row["pv_usd"]),
                "weight_pct": float(row["weight_pct"]),
                "position_count": row["position_count"],
                "pv_local": float(row["pv_local"]),
                "avg_fx_rate": float(row["avg_fx_rate"]),
            }
            for row in rows
        ]

        return {
            "portfolio_id": portfolio_id,
            "group_by": "currency",
            "measure": "market_value",
            "total": float(total),
            "buckets": buckets
        }


@router.get("/{portfolio_id}/by-product-type")
def aggregate_by_product_type(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for valuation data"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
):
    """Aggregate portfolio exposure grouped by product type."""
    query, params = build_product_type_aggregation_query(portfolio_id, run_id, snapshot_id)

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return {
                "portfolio_id": portfolio_id,
                "group_by": "product_type",
                "measure": "market_value",
                "total": 0.0,
                "buckets": []
            }

        total = sum(row["pv_usd"] for row in rows)
        buckets = [
            {
                "key": row["product_type"],
                "value": float(row["pv_usd"]),
                "weight_pct": float(row["weight_pct"]),
                "position_count": row["position_count"],
            }
            for row in rows
        ]

        return {
            "portfolio_id": portfolio_id,
            "group_by": "product_type",
            "measure": "market_value",
            "total": float(total),
            "buckets": buckets
        }
