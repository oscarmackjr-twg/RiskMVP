"""Aggregation endpoints - group by issuer, sector, rating, geography, etc."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

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


# ---------------------------------------------------------------------------
# Portfolio Metrics
# ---------------------------------------------------------------------------

class CurrencyBreakdown(BaseModel):
    """Currency breakdown entry."""
    ccy: str
    market_value: float
    weight_pct: float


class PortfolioMetrics(BaseModel):
    """Portfolio-level metrics (PORT-08 requirements)."""
    market_value_usd: float = 0.0
    book_value_usd: float = 0.0
    accrued_interest_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    realized_pnl_usd: float = 0.0
    portfolio_yield_pct: Optional[float] = None
    weighted_average_maturity_years: Optional[float] = None
    weighted_average_life_years: Optional[float] = None
    position_count: int = 0
    instrument_count: int = 0


class PortfolioMetricsResponse(BaseModel):
    """Portfolio metrics response."""
    portfolio_node_id: str
    run_id: Optional[str] = None
    as_of_date: Optional[datetime] = None
    metrics: PortfolioMetrics
    currency_breakdown: List[CurrencyBreakdown] = Field(default_factory=list)


@router.get("/{portfolio_id}/metrics", response_model=PortfolioMetricsResponse)
def get_portfolio_metrics(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for valuation data"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
):
    """Calculate portfolio-level metrics (PORT-08 requirements)."""

    # Main metrics query
    metrics_query = """
    WITH position_metrics AS (
      SELECT
        pos.position_id,
        pos.instrument_id,
        pos.base_ccy,
        pos.book_value,
        (vr.measures_json ->> 'PV')::numeric AS pv_local,
        (vr.measures_json ->> 'ACCRUED_INTEREST')::numeric AS accrued_local,
        (vr.measures_json ->> 'YTM')::numeric AS ytm,
        (iv.terms_json ->> 'maturity_years')::numeric AS maturity_years,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'ACCRUED_INTEREST')::numeric
          ELSE (vr.measures_json ->> 'ACCRUED_INTEREST')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS accrued_usd,
        CASE
          WHEN pos.base_ccy = 'USD' THEN pos.book_value
          ELSE pos.book_value * COALESCE(fx.spot_rate, 1.0)
        END AS book_value_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      COALESCE(SUM(pv_usd), 0) AS market_value_usd,
      COALESCE(SUM(book_value_usd), 0) AS book_value_usd,
      COALESCE(SUM(accrued_usd), 0) AS accrued_interest_usd,
      COALESCE(SUM(pv_usd) - SUM(book_value_usd), 0) AS unrealized_pnl_usd,
      CASE
        WHEN SUM(pv_usd) > 0 THEN 100.0 * SUM(ytm * pv_usd) / NULLIF(SUM(pv_usd), 0)
        ELSE NULL
      END AS portfolio_yield_pct,
      CASE
        WHEN SUM(pv_usd) > 0 THEN SUM(maturity_years * pv_usd) / NULLIF(SUM(pv_usd), 0)
        ELSE NULL
      END AS weighted_average_maturity_years,
      COUNT(DISTINCT position_id) AS position_count,
      COUNT(DISTINCT instrument_id) AS instrument_count
    FROM position_metrics;
    """

    # Currency breakdown query
    currency_query = """
    WITH position_pv AS (
      SELECT
        pos.base_ccy,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      base_ccy AS ccy,
      COALESCE(SUM(pv_usd), 0) AS market_value,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY base_ccy
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY market_value DESC;
    """

    params = {
        "port_id": portfolio_id,
        "rid": run_id,
        "sid": snapshot_id,
    }

    with db_conn() as conn:
        # Get main metrics
        metrics_row = conn.execute(metrics_query, params).fetchone()

        # Get currency breakdown
        currency_rows = conn.execute(currency_query, params).fetchall()

        # Get run metadata if run_id provided
        as_of_date = None
        if run_id:
            run_row = conn.execute(
                "SELECT created_at FROM run WHERE run_id = %(rid)s",
                {"rid": run_id}
            ).fetchone()
            if run_row:
                as_of_date = run_row["created_at"]

        metrics = PortfolioMetrics(
            market_value_usd=float(metrics_row["market_value_usd"]),
            book_value_usd=float(metrics_row["book_value_usd"]),
            accrued_interest_usd=float(metrics_row["accrued_interest_usd"]),
            unrealized_pnl_usd=float(metrics_row["unrealized_pnl_usd"]),
            realized_pnl_usd=0.0,  # Track separately in position.realized_pnl_json if available
            portfolio_yield_pct=float(metrics_row["portfolio_yield_pct"]) if metrics_row["portfolio_yield_pct"] else None,
            weighted_average_maturity_years=float(metrics_row["weighted_average_maturity_years"]) if metrics_row["weighted_average_maturity_years"] else None,
            weighted_average_life_years=None,  # WAL measure would come from valuation_result if available
            position_count=metrics_row["position_count"],
            instrument_count=metrics_row["instrument_count"],
        )

        currency_breakdown = [
            CurrencyBreakdown(
                ccy=row["ccy"],
                market_value=float(row["market_value"]),
                weight_pct=float(row["weight_pct"])
            )
            for row in currency_rows
        ]

        return PortfolioMetricsResponse(
            portfolio_node_id=portfolio_id,
            run_id=run_id,
            as_of_date=as_of_date,
            metrics=metrics,
            currency_breakdown=currency_breakdown
        )
