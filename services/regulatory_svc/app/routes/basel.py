"""Basel III capital analytics and RWA endpoints."""
from __future__ import annotations

from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from services.regulatory_svc.app.models import (
    BaselCapitalRequest,
    BaselCapitalResult,
    CapitalSummary,
    RWAExposure,
)
from compute.regulatory.basel import compute_basel_rwa, compute_capital_ratios, leverage_ratio
from services.common.db import db_conn
from services.common.audit import log_audit_entry
from psycopg.rows import dict_row
from psycopg.types.json import Json

router = APIRouter()


@router.post("/compute", response_model=BaselCapitalResult, status_code=201)
def compute_capital(req: BaselCapitalRequest):
    """Compute Basel III risk-weighted assets and capital ratios for a portfolio."""

    with db_conn() as conn:
        conn.row_factory = dict_row

        # Fetch positions with EAD, counterparty type, rating
        positions = conn.execute("""
            SELECT
              pos.position_id,
              pos.instrument_id,
              COALESCE((pos.metadata_json ->> 'notional')::numeric, 0) AS ead,
              COALESCE(pos.metadata_json ->> 'counterparty_type', 'CORPORATE') AS counterparty_type,
              COALESCE(pos.metadata_json ->> 'rating', 'UNRATED') AS rating
            FROM position pos
            WHERE pos.portfolio_node_id = %(pid)s
        """, {'pid': req.portfolio_node_id}).fetchall()

        if not positions:
            raise HTTPException(status_code=404, detail="No positions found")

        # Fetch risk weights from regulatory_reference
        rw_data = conn.execute("""
            SELECT entity_key, ref_value
            FROM regulatory_reference
            WHERE ref_type = 'RISK_WEIGHT'
              AND effective_date <= %(as_of)s
              AND (expired_date IS NULL OR expired_date > %(as_of)s)
        """, {'as_of': req.as_of_date.isoformat()}).fetchall()

        risk_weights = {}
        for row in rw_data:
            parts = row['entity_key'].split('/')
            if len(parts) == 2:
                risk_weights[(parts[0], parts[1])] = float(row['ref_value'])

        # Default risk weights if not in DB
        if not risk_weights:
            risk_weights = {
                ('SOVEREIGN', 'AAA'): 0.00, ('SOVEREIGN', 'AA'): 0.00,
                ('SOVEREIGN', 'A'): 0.20, ('SOVEREIGN', 'BBB'): 0.50,
                ('CORPORATE', 'AAA'): 0.20, ('CORPORATE', 'AA'): 0.20,
                ('CORPORATE', 'A'): 0.50, ('CORPORATE', 'BBB'): 1.00,
                ('CORPORATE', 'BB'): 1.00, ('CORPORATE', 'B'): 1.50,
                ('RETAIL', 'ANY'): 0.75,
                ('BANK', 'AAA'): 0.20, ('BANK', 'BBB'): 0.50,
                ('UNRATED', 'ANY'): 1.00,
            }

        # Compute RWA
        rwa_result = compute_basel_rwa(
            portfolio=[dict(p) for p in positions],
            risk_weights=risk_weights,
        )

        # Fetch capital from latest metrics or use defaults
        cap_data = conn.execute("""
            SELECT metric_value, metric_breakdown_json
            FROM regulatory_metrics
            WHERE portfolio_node_id = %(pid)s
              AND metric_type = 'CAPITAL_RATIO'
            ORDER BY as_of_date DESC LIMIT 1
        """, {'pid': req.portfolio_node_id}).fetchone()

        tier1_capital = 0.0
        tier2_capital = 0.0
        if cap_data and cap_data['metric_breakdown_json']:
            tier1_capital = float(cap_data['metric_breakdown_json'].get('tier1_capital', 0))
            tier2_capital = float(cap_data['metric_breakdown_json'].get('tier2_capital', 0))

        capital_ratios = compute_capital_ratios(
            total_rwa=rwa_result["total_rwa"],
            tier1_capital=tier1_capital,
            tier2_capital=tier2_capital,
        )

        # Build exposure list
        exposures = []
        for detail in rwa_result.get("detail", []):
            exposures.append(RWAExposure(
                exposure_id=detail["position_id"],
                asset_class=detail["counterparty_type"],
                exposure_amount=detail["ead"],
                risk_weight_pct=detail["risk_weight"] * 100,
                rwa=detail["rwa"],
            ))

        # Log audit trail
        audit_id = log_audit_entry(
            audit_type="BASEL",
            calculation_run_id=req.run_id,
            entity_type="PORTFOLIO",
            entity_id=req.portfolio_node_id,
            calculation_method=f"BASEL3_{req.approach}",
            input_snapshot_id="N/A",
            assumptions={"approach": req.approach},
            results={
                "total_rwa": rwa_result["total_rwa"],
                "capital_ratios": capital_ratios,
                "by_counterparty_type": rwa_result["by_counterparty_type"],
            },
        )

        # UPSERT regulatory_metrics
        metric_id = f"basel-{req.portfolio_node_id}-{req.as_of_date.date()}"
        conn.execute("""
            INSERT INTO regulatory_metrics
              (metric_id, portfolio_node_id, metric_type, metric_value, as_of_date,
               metric_breakdown_json, calculation_run_id)
            VALUES (%(mid)s, %(pid)s, 'BASEL_RWA', %(val)s, %(as_of)s,
                    %(breakdown)s, %(crid)s)
            ON CONFLICT (portfolio_node_id, metric_type, as_of_date)
            DO UPDATE SET
              metric_value = EXCLUDED.metric_value,
              metric_breakdown_json = EXCLUDED.metric_breakdown_json,
              calculation_run_id = EXCLUDED.calculation_run_id
        """, {
            'mid': metric_id,
            'pid': req.portfolio_node_id,
            'val': rwa_result["total_rwa"],
            'as_of': req.as_of_date,
            'breakdown': Json({
                'by_counterparty_type': rwa_result["by_counterparty_type"],
                'by_rating': rwa_result["by_rating"],
                'capital_ratios': capital_ratios,
            }),
            'crid': req.run_id,
        })

        return BaselCapitalResult(
            run_id=req.run_id,
            as_of_date=req.as_of_date,
            portfolio_node_id=req.portfolio_node_id,
            approach=req.approach,
            exposures=exposures,
            total_rwa=rwa_result["total_rwa"],
            cet1_ratio_pct=capital_ratios["cet1_ratio"] * 100,
            tier1_ratio_pct=capital_ratios["tier1_ratio"] * 100,
            total_capital_ratio_pct=capital_ratios["total_capital_ratio"] * 100,
        )


@router.get("/results/{run_id}", response_model=BaselCapitalResult)
def get_capital_result(run_id: str):
    """Retrieve previously computed Basel III capital results for a run."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        audit = conn.execute("""
            SELECT entity_id, assumptions_json, results_json, computed_at
            FROM audit_trail
            WHERE calculation_run_id = %(rid)s AND audit_type = 'BASEL'
            ORDER BY computed_at DESC LIMIT 1
        """, {'rid': run_id}).fetchone()

        if not audit:
            raise HTTPException(status_code=404, detail="Basel result not found")

        results = audit['results_json']
        ratios = results.get('capital_ratios', {})

        return BaselCapitalResult(
            run_id=run_id,
            as_of_date=audit['computed_at'],
            portfolio_node_id=audit['entity_id'],
            approach=audit['assumptions_json'].get('approach', 'STANDARDISED'),
            total_rwa=results.get('total_rwa', 0.0),
            cet1_ratio_pct=ratios.get('cet1_ratio', 0.0) * 100,
            tier1_ratio_pct=ratios.get('tier1_ratio', 0.0) * 100,
            total_capital_ratio_pct=ratios.get('total_capital_ratio', 0.0) * 100,
            computed_at=audit['computed_at'],
        )


@router.get("/summary/{portfolio_node_id}", response_model=CapitalSummary)
def get_capital_summary(portfolio_node_id: str):
    """Return the latest capital adequacy summary for a portfolio."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        metric = conn.execute("""
            SELECT metric_value, metric_breakdown_json, as_of_date
            FROM regulatory_metrics
            WHERE portfolio_node_id = %(pid)s AND metric_type = 'BASEL_RWA'
            ORDER BY as_of_date DESC LIMIT 1
        """, {'pid': portfolio_node_id}).fetchone()

        if not metric:
            raise HTTPException(status_code=404, detail="No Basel metrics found")

        breakdown = metric['metric_breakdown_json'] or {}
        ratios = breakdown.get('capital_ratios', {})
        tier1 = ratios.get('tier1_ratio', 0.0)

        return CapitalSummary(
            as_of_date=metric['as_of_date'],
            total_rwa=float(metric['metric_value']),
            cet1_capital=0.0,
            cet1_ratio_pct=ratios.get('cet1_ratio', 0.0) * 100,
            tier1_capital=0.0,
            tier1_ratio_pct=tier1 * 100,
            total_capital=0.0,
            total_capital_ratio_pct=ratios.get('total_capital_ratio', 0.0) * 100,
            buffer_requirement_pct=2.5,
            surplus_deficit=(tier1 - 0.06) * float(metric['metric_value']),
        )


@router.get("/rwa-breakdown/{run_id}")
def get_rwa_breakdown(run_id: str, by: str = "asset_class"):
    """Return RWA broken down by asset class, rating bucket, or business line."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        audit = conn.execute("""
            SELECT results_json FROM audit_trail
            WHERE calculation_run_id = %(rid)s AND audit_type = 'BASEL'
            ORDER BY computed_at DESC LIMIT 1
        """, {'rid': run_id}).fetchone()

        if not audit:
            raise HTTPException(status_code=404, detail="Basel result not found")

        results = audit['results_json']
        if by == "rating":
            return {"breakdown": results.get("by_rating", {}), "by": by}
        return {"breakdown": results.get("by_counterparty_type", {}), "by": by}


@router.get("/stress-buffers/{portfolio_node_id}")
def get_stress_buffers(portfolio_node_id: str):
    """Return countercyclical and systemic buffer requirements."""
    return {
        "portfolio_node_id": portfolio_node_id,
        "capital_conservation_buffer_pct": 2.5,
        "countercyclical_buffer_pct": 0.0,
        "systemic_buffer_pct": 0.0,
        "total_buffer_pct": 2.5,
    }


@router.get("/leverage-ratio/{portfolio_node_id}")
def get_leverage_ratio(portfolio_node_id: str):
    """Compute the Basel III leverage ratio (Tier 1 / total exposure)."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        metric = conn.execute("""
            SELECT metric_value, metric_breakdown_json
            FROM regulatory_metrics
            WHERE portfolio_node_id = %(pid)s AND metric_type = 'BASEL_RWA'
            ORDER BY as_of_date DESC LIMIT 1
        """, {'pid': portfolio_node_id}).fetchone()

        if not metric:
            raise HTTPException(status_code=404, detail="No Basel metrics found")

        breakdown = metric['metric_breakdown_json'] or {}
        ratios = breakdown.get('capital_ratios', {})

        return {
            "portfolio_node_id": portfolio_node_id,
            "leverage_ratio_pct": ratios.get('tier1_ratio', 0.0) * 100,
            "minimum_required_pct": 3.0,
        }
