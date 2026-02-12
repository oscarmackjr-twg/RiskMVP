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


# ---------------------------------------------------------------------------
# Concentration Risk Monitoring (RISK-06)
# ---------------------------------------------------------------------------

class ConcentrationViolation(BaseModel):
    """Concentration threshold violation."""
    dimension: str
    entity: str
    weight_pct: float
    threshold_pct: float
    excess_pct: float


class ConcentrationBucket(BaseModel):
    """Concentration bucket with entity and weight."""
    entity: str
    weight_pct: float
    pv_usd: float


class ConcentrationReport(BaseModel):
    """Concentration risk analysis report."""
    portfolio_node_id: str
    run_id: Optional[str] = None
    concentration_threshold: float
    violations: List[ConcentrationViolation] = Field(default_factory=list)
    top_10_issuers: List[ConcentrationBucket] = Field(default_factory=list)
    top_5_sectors: List[ConcentrationBucket] = Field(default_factory=list)
    herfindahl_index: float = 0.0
    diversification_ratio: float = 0.0


@router.get("/{portfolio_id}/concentration", response_model=ConcentrationReport)
def analyze_concentration(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for valuation data"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
    concentration_threshold: float = Query(10.0, description="Threshold percentage for violations"),
):
    """Analyze portfolio concentration across multiple dimensions (RISK-06)."""

    # Build multi-dimensional concentration query
    concentration_query = """
    WITH position_pv AS (
      SELECT
        pos.position_id,
        pos.instrument_id,
        ref.entity_id AS issuer_id,
        ref.name AS issuer_name,
        ref.sector,
        ref.geography,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN reference_data ref ON (iv.terms_json ->> 'issuer_id') = ref.entity_id
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    ),
    portfolio_total AS (
      SELECT COALESCE(SUM(pv_usd), 0) AS total_pv FROM position_pv
    ),
    issuer_concentration AS (
      SELECT
        'issuer' AS dimension,
        COALESCE(issuer_name, 'Unknown') AS entity,
        SUM(pv_usd) AS pv_usd,
        ROUND(100.0 * SUM(pv_usd) / NULLIF((SELECT total_pv FROM portfolio_total), 0), 2) AS weight_pct
      FROM position_pv
      GROUP BY issuer_name
      HAVING SUM(pv_usd) IS NOT NULL
    ),
    sector_concentration AS (
      SELECT
        'sector' AS dimension,
        COALESCE(sector, 'Unknown') AS entity,
        SUM(pv_usd) AS pv_usd,
        ROUND(100.0 * SUM(pv_usd) / NULLIF((SELECT total_pv FROM portfolio_total), 0), 2) AS weight_pct
      FROM position_pv
      GROUP BY sector
      HAVING SUM(pv_usd) IS NOT NULL
    ),
    geography_concentration AS (
      SELECT
        'geography' AS dimension,
        COALESCE(geography, 'Unknown') AS entity,
        SUM(pv_usd) AS pv_usd,
        ROUND(100.0 * SUM(pv_usd) / NULLIF((SELECT total_pv FROM portfolio_total), 0), 2) AS weight_pct
      FROM position_pv
      GROUP BY geography
      HAVING SUM(pv_usd) IS NOT NULL
    ),
    single_name_concentration AS (
      SELECT
        'single_position' AS dimension,
        instrument_id AS entity,
        pv_usd,
        ROUND(100.0 * pv_usd / NULLIF((SELECT total_pv FROM portfolio_total), 0), 2) AS weight_pct
      FROM position_pv
      WHERE pv_usd IS NOT NULL
    ),
    all_concentrations AS (
      SELECT * FROM issuer_concentration
      UNION ALL
      SELECT * FROM sector_concentration
      UNION ALL
      SELECT * FROM geography_concentration
      UNION ALL
      SELECT * FROM single_name_concentration
    )
    SELECT dimension, entity, pv_usd, weight_pct
    FROM all_concentrations
    WHERE weight_pct > %(threshold)s
    ORDER BY weight_pct DESC;
    """

    # Top issuers query
    top_issuers_query = """
    WITH position_pv AS (
      SELECT
        ref.name AS issuer_name,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN reference_data ref ON (iv.terms_json ->> 'issuer_id') = ref.entity_id
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      COALESCE(issuer_name, 'Unknown') AS entity,
      SUM(pv_usd) AS pv_usd,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY issuer_name
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY pv_usd DESC
    LIMIT 10;
    """

    # Top sectors query
    top_sectors_query = """
    WITH position_pv AS (
      SELECT
        ref.sector,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN reference_data ref ON (iv.terms_json ->> 'issuer_id') = ref.entity_id
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      COALESCE(sector, 'Unknown') AS entity,
      SUM(pv_usd) AS pv_usd,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY sector
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY pv_usd DESC
    LIMIT 5;
    """

    # Herfindahl index query (sum of squared weights)
    herfindahl_query = """
    WITH position_pv AS (
      SELECT
        pos.position_id,
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
    ),
    portfolio_total AS (
      SELECT COALESCE(SUM(pv_usd), 0) AS total_pv FROM position_pv
    ),
    position_weights AS (
      SELECT
        pv_usd / NULLIF((SELECT total_pv FROM portfolio_total), 0) AS weight
      FROM position_pv
      WHERE pv_usd IS NOT NULL
    )
    SELECT
      COALESCE(SUM(weight * weight), 0) AS herfindahl_index
    FROM position_weights;
    """

    params = {
        "port_id": portfolio_id,
        "rid": run_id,
        "sid": snapshot_id,
        "threshold": concentration_threshold,
    }

    with db_conn() as conn:
        # Get concentration violations
        violation_rows = conn.execute(concentration_query, params).fetchall()
        violations = [
            ConcentrationViolation(
                dimension=row["dimension"],
                entity=row["entity"],
                weight_pct=float(row["weight_pct"]),
                threshold_pct=concentration_threshold,
                excess_pct=float(row["weight_pct"]) - concentration_threshold,
            )
            for row in violation_rows
        ]

        # Get top 10 issuers
        issuer_rows = conn.execute(top_issuers_query, params).fetchall()
        top_issuers = [
            ConcentrationBucket(
                entity=row["entity"],
                weight_pct=float(row["weight_pct"]),
                pv_usd=float(row["pv_usd"]),
            )
            for row in issuer_rows
        ]

        # Get top 5 sectors
        sector_rows = conn.execute(top_sectors_query, params).fetchall()
        top_sectors = [
            ConcentrationBucket(
                entity=row["entity"],
                weight_pct=float(row["weight_pct"]),
                pv_usd=float(row["pv_usd"]),
            )
            for row in sector_rows
        ]

        # Get Herfindahl index
        herfindahl_row = conn.execute(herfindahl_query, params).fetchone()
        herfindahl_index = float(herfindahl_row["herfindahl_index"]) if herfindahl_row else 0.0

        # Calculate diversification ratio
        import math
        diversification_ratio = 1.0 / math.sqrt(herfindahl_index) if herfindahl_index > 0 else 0.0

        return ConcentrationReport(
            portfolio_node_id=portfolio_id,
            run_id=run_id,
            concentration_threshold=concentration_threshold,
            violations=violations,
            top_10_issuers=top_issuers,
            top_5_sectors=top_sectors,
            herfindahl_index=herfindahl_index,
            diversification_ratio=diversification_ratio,
        )


# ---------------------------------------------------------------------------
# Rating Migration Tracking
# ---------------------------------------------------------------------------

class RatingMigration(BaseModel):
    """Rating migration event."""
    entity_id: str
    entity_name: Optional[str] = None
    agency: str
    old_rating: str
    new_rating: str
    old_date: datetime
    new_date: datetime
    direction: str  # "upgrade", "downgrade", "watchlist"
    notches: int
    portfolio_exposure_usd: float


class RatingMigrationReport(BaseModel):
    """Rating migration tracking report."""
    portfolio_node_id: str
    date_from: datetime
    date_to: datetime
    migrations: List[RatingMigration] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


@router.get("/{portfolio_id}/rating-migration", response_model=RatingMigrationReport)
def track_rating_migrations(
    portfolio_id: str,
    date_from: datetime = Query(..., description="From date"),
    date_to: datetime = Query(..., description="To date"),
    run_id: Optional[str] = Query(None, description="Run ID for exposure calculation"),
    snapshot_id: Optional[str] = Query(None, description="Snapshot ID for FX rates"),
):
    """Track rating migrations for portfolio issuers (RISK-06)."""

    migration_query = """
    WITH position_issuers AS (
      SELECT DISTINCT
        (iv.terms_json ->> 'issuer_id') AS issuer_id,
        ref.name AS issuer_name
      FROM position pos
      JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN reference_data ref ON (iv.terms_json ->> 'issuer_id') = ref.entity_id
      WHERE pos.portfolio_node_id = %(pid)s AND pos.status = 'ACTIVE'
    ),
    issuer_exposure AS (
      SELECT
        (iv.terms_json ->> 'issuer_id') AS issuer_id,
        SUM(CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END) AS exposure_usd
      FROM position pos
      JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(pid)s AND pos.status = 'ACTIVE'
      GROUP BY (iv.terms_json ->> 'issuer_id')
    )
    SELECT
      rh1.entity_id,
      pi.issuer_name,
      rh1.agency,
      rh1.rating AS old_rating,
      rh2.rating AS new_rating,
      rh1.as_of_date AS old_date,
      rh2.as_of_date AS new_date,
      COALESCE(ie.exposure_usd, 0) AS portfolio_exposure_usd
    FROM rating_history rh1
    JOIN rating_history rh2 ON rh1.entity_id = rh2.entity_id
      AND rh1.agency = rh2.agency
      AND rh2.as_of_date > rh1.as_of_date
    JOIN position_issuers pi ON rh1.entity_id = pi.issuer_id
    LEFT JOIN issuer_exposure ie ON rh1.entity_id = ie.issuer_id
    WHERE rh1.as_of_date >= %(from)s
      AND rh2.as_of_date <= %(to)s
      AND rh1.rating != rh2.rating
      AND NOT EXISTS (
        SELECT 1 FROM rating_history rh3
        WHERE rh3.entity_id = rh1.entity_id
          AND rh3.agency = rh1.agency
          AND rh3.as_of_date > rh1.as_of_date
          AND rh3.as_of_date < rh2.as_of_date
      )
    ORDER BY rh2.as_of_date DESC;
    """

    params = {
        "pid": portfolio_id,
        "from": date_from,
        "to": date_to,
        "rid": run_id,
        "sid": snapshot_id,
    }

    # Simple rating scale for notch calculation (S&P style)
    rating_scale = {
        "AAA": 21, "AA+": 20, "AA": 19, "AA-": 18,
        "A+": 17, "A": 16, "A-": 15,
        "BBB+": 14, "BBB": 13, "BBB-": 12,
        "BB+": 11, "BB": 10, "BB-": 9,
        "B+": 8, "B": 7, "B-": 6,
        "CCC+": 5, "CCC": 4, "CCC-": 3,
        "CC": 2, "C": 1, "D": 0,
    }

    with db_conn() as conn:
        rows = conn.execute(migration_query, params).fetchall()

        migrations = []
        for row in rows:
            old_rating = row["old_rating"]
            new_rating = row["new_rating"]

            # Determine direction and notches
            old_score = rating_scale.get(old_rating, 0)
            new_score = rating_scale.get(new_rating, 0)
            notches = new_score - old_score

            if notches > 0:
                direction = "upgrade"
            elif notches < 0:
                direction = "downgrade"
            else:
                direction = "watchlist"

            migrations.append(
                RatingMigration(
                    entity_id=row["entity_id"],
                    entity_name=row["issuer_name"],
                    agency=row["agency"],
                    old_rating=old_rating,
                    new_rating=new_rating,
                    old_date=row["old_date"],
                    new_date=row["new_date"],
                    direction=direction,
                    notches=abs(notches),
                    portfolio_exposure_usd=float(row["portfolio_exposure_usd"]),
                )
            )

        # Build summary
        summary = {
            "total_migrations": len(migrations),
            "upgrades": len([m for m in migrations if m.direction == "upgrade"]),
            "downgrades": len([m for m in migrations if m.direction == "downgrade"]),
            "total_exposure_affected_usd": sum(m.portfolio_exposure_usd for m in migrations),
        }

        return RatingMigrationReport(
            portfolio_node_id=portfolio_id,
            date_from=date_from,
            date_to=date_to,
            migrations=migrations,
            summary=summary,
        )
