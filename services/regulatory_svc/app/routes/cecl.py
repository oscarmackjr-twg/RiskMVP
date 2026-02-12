"""CECL / Expected Credit Loss endpoints."""
from __future__ import annotations

from typing import Dict, Any, List
from uuid import uuid4
from fastapi import APIRouter, HTTPException

from services.regulatory_svc.app.models import (
    CECLRequest,
    CECLResult,
    CECLSegment,
    CECLHistoryEntry,
)
from compute.regulatory.cecl import compute_cecl_allowance, stage_classification
from services.common.db import db_conn
from services.common.audit import log_audit_entry
from psycopg.rows import dict_row
from psycopg.types.json import Json

router = APIRouter()


@router.post("/compute", response_model=CECLResult, status_code=201)
def compute_cecl(req: CECLRequest):
    """Compute CECL expected credit losses for a portfolio under a given methodology and scenario."""

    with db_conn() as conn:
        conn.row_factory = dict_row

        # Fetch portfolio positions with EAD, rating, issuer
        positions = conn.execute("""
            SELECT
              pos.position_id,
              pos.instrument_id,
              COALESCE((pos.metadata_json ->> 'notional')::numeric, 0) AS ead,
              COALESCE(pos.metadata_json ->> 'issuer_id', 'unknown') AS issuer_id,
              COALESCE(pos.metadata_json ->> 'rating', 'BBB') AS rating,
              pos.base_ccy
            FROM position pos
            LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
            WHERE pos.portfolio_node_id = %(pid)s
              AND COALESCE(instr.product_type, '') IN ('AMORT_LOAN', 'FIXED_BOND', 'FLOATING_RATE_NOTE', '')
        """, {'pid': req.portfolio_node_id}).fetchall()

        if not positions:
            raise HTTPException(status_code=404, detail="No positions found for CECL computation")

        # Fetch PD curves from regulatory_reference
        pd_curves: Dict[str, List[float]] = {}
        pd_data = conn.execute("""
            SELECT entity_key AS rating, ref_value AS pd_annual
            FROM regulatory_reference
            WHERE ref_type = 'PD_CURVE'
              AND effective_date <= %(as_of)s
              AND (expired_date IS NULL OR expired_date > %(as_of)s)
            ORDER BY entity_key, effective_date DESC
        """, {'as_of': req.as_of_date.isoformat()}).fetchall()

        for row in pd_data:
            rating = row['rating']
            if rating not in pd_curves:
                pd_curves[rating] = []
            pd_curves[rating].append(float(row['pd_annual']))

        # Default PD curves if none in DB
        if not pd_curves:
            pd_curves = {
                "AAA": [0.005, 0.007, 0.009, 0.011, 0.013],
                "AA": [0.008, 0.010, 0.013, 0.016, 0.019],
                "A": [0.010, 0.015, 0.018, 0.021, 0.024],
                "BBB": [0.010, 0.015, 0.020, 0.025, 0.030],
                "BB": [0.030, 0.045, 0.060, 0.075, 0.090],
                "B": [0.060, 0.080, 0.100, 0.120, 0.140],
            }

        # LGD assumptions
        lgd_assumptions = {"default": 0.45}

        # Macro scenarios based on request
        scenario_map = {
            "BASE": ([{"base_rate": 2.5, "unemployment": 4.2}], [1.0]),
            "ADVERSE": ([{"base_rate": 4.5, "unemployment": 7.0}], [1.0]),
            "SEVERELY_ADVERSE": ([{"base_rate": 6.0, "unemployment": 10.0}], [1.0]),
        }
        macro_scenarios, scenario_weights = scenario_map.get(
            req.forecast_scenario, scenario_map["BASE"]
        )

        # Q-factor from qualitative factors
        q_factor = sum(req.qualitative_factors.values()) if req.qualitative_factors else 0.0

        # Compute CECL allowance
        result = compute_cecl_allowance(
            portfolio=[dict(p) for p in positions],
            pd_curves=pd_curves,
            lgd_assumptions=lgd_assumptions,
            macro_scenarios=macro_scenarios,
            scenario_weights=scenario_weights,
            q_factor=q_factor,
        )

        # Build segment list
        segments = []
        total_outstanding = sum(float(p.get('ead', 0)) for p in positions)
        for seg_id, ecl in result["by_segment"].items():
            seg_positions = [p for p in positions if p.get('issuer_id', 'unknown') == seg_id]
            seg_balance = sum(float(sp.get('ead', 0)) for sp in seg_positions)
            segments.append(CECLSegment(
                segment_id=seg_id,
                segment_name=seg_id,
                outstanding_balance=seg_balance,
                expected_loss_rate=(ecl / seg_balance * 100) if seg_balance > 0 else 0.0,
                expected_credit_loss=ecl,
                qualitative_adjustment=q_factor,
            ))

        # Log to audit trail
        audit_id = log_audit_entry(
            audit_type="CECL",
            calculation_run_id=req.run_id,
            entity_type="PORTFOLIO",
            entity_id=req.portfolio_node_id,
            calculation_method=f"ASC326_{req.methodology}",
            input_snapshot_id="N/A",
            assumptions={
                "methodology": req.methodology,
                "forecast_scenario": req.forecast_scenario,
                "q_factor": q_factor,
                "lgd_default": lgd_assumptions["default"],
            },
            results={
                "total_ecl": result["total_allowance"],
                "by_segment": result["by_segment"],
            },
        )

        # UPSERT to regulatory_metrics
        metric_id = f"cecl-{req.portfolio_node_id}-{req.as_of_date.date()}"
        conn.execute("""
            INSERT INTO regulatory_metrics
              (metric_id, portfolio_node_id, metric_type, metric_value, as_of_date,
               metric_breakdown_json, calculation_run_id)
            VALUES (%(mid)s, %(pid)s, 'CECL_ALLOWANCE', %(val)s, %(as_of)s,
                    %(breakdown)s, %(crid)s)
            ON CONFLICT (portfolio_node_id, metric_type, as_of_date)
            DO UPDATE SET
              metric_value = EXCLUDED.metric_value,
              metric_breakdown_json = EXCLUDED.metric_breakdown_json,
              calculation_run_id = EXCLUDED.calculation_run_id
        """, {
            'mid': metric_id,
            'pid': req.portfolio_node_id,
            'val': result["total_allowance"],
            'as_of': req.as_of_date,
            'breakdown': Json({
                'by_segment': result["by_segment"],
                'scenario_detail': result.get("scenario_detail", []),
            }),
            'crid': req.run_id,
        })

        reserve_rate = (result["total_allowance"] / total_outstanding * 100) if total_outstanding > 0 else 0.0

        return CECLResult(
            run_id=req.run_id,
            as_of_date=req.as_of_date,
            portfolio_node_id=req.portfolio_node_id,
            methodology=req.methodology,
            forecast_scenario=req.forecast_scenario,
            segments=segments,
            total_outstanding=total_outstanding,
            total_ecl=result["total_allowance"],
            reserve_rate_pct=reserve_rate,
        )


@router.get("/results/{run_id}", response_model=CECLResult)
def get_cecl_result(run_id: str):
    """Retrieve previously computed CECL results for a run."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        audit = conn.execute("""
            SELECT entity_id, assumptions_json, results_json, computed_at
            FROM audit_trail
            WHERE calculation_run_id = %(rid)s AND audit_type = 'CECL'
            ORDER BY computed_at DESC LIMIT 1
        """, {'rid': run_id}).fetchone()

        if not audit:
            raise HTTPException(status_code=404, detail="CECL result not found")

        results = audit['results_json']
        assumptions = audit['assumptions_json']

        segments = []
        for seg_id, ecl in results.get('by_segment', {}).items():
            segments.append(CECLSegment(
                segment_id=seg_id,
                segment_name=seg_id,
                outstanding_balance=0.0,
                expected_loss_rate=0.0,
                expected_credit_loss=ecl,
            ))

        return CECLResult(
            run_id=run_id,
            as_of_date=audit['computed_at'],
            portfolio_node_id=audit['entity_id'],
            methodology=assumptions.get('methodology', 'PD_LGD'),
            forecast_scenario=assumptions.get('forecast_scenario', 'BASE'),
            segments=segments,
            total_ecl=results.get('total_ecl', 0.0),
            computed_at=audit['computed_at'],
        )


@router.get("/history/{portfolio_node_id}", response_model=list[CECLHistoryEntry])
def get_cecl_history(portfolio_node_id: str, limit: int = 12):
    """Return the time-series of CECL reserves for a portfolio."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        rows = conn.execute("""
            SELECT as_of_date, metric_value AS total_ecl,
                   metric_breakdown_json
            FROM regulatory_metrics
            WHERE portfolio_node_id = %(pid)s
              AND metric_type = 'CECL_ALLOWANCE'
            ORDER BY as_of_date DESC
            LIMIT %(limit)s
        """, {'pid': portfolio_node_id, 'limit': limit}).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="No CECL history found")

        return [
            CECLHistoryEntry(
                as_of_date=row['as_of_date'],
                total_ecl=float(row['total_ecl']),
                reserve_rate_pct=0.0,
                methodology="PD_LGD",
            )
            for row in rows
        ]


@router.get("/methodologies")
def list_methodologies():
    """List available CECL computation methodologies."""
    return [
        {"id": "PD_LGD", "name": "PD/LGD Model", "description": "Probability of default times loss given default"},
        {"id": "WARM", "name": "Weighted Average Remaining Maturity", "description": "Loss rate times remaining maturity"},
        {"id": "DCF", "name": "Discounted Cash Flow", "description": "Present value of expected cash shortfalls"},
        {"id": "VINTAGE", "name": "Vintage Analysis", "description": "Historical loss rates by origination cohort"},
    ]


@router.get("/staging/{portfolio_id}")
def get_cecl_staging(portfolio_id: str):
    """Get CECL stage classification for portfolio positions."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        positions = conn.execute("""
            SELECT
              pos.position_id,
              COALESCE((pos.metadata_json ->> 'current_pd')::numeric, 0.02) AS current_pd,
              COALESCE((pos.metadata_json ->> 'origination_pd')::numeric, 0.01) AS origination_pd,
              COALESCE((pos.metadata_json ->> 'days_past_due')::int, 0) AS days_past_due
            FROM position pos
            WHERE pos.portfolio_node_id = %(pid)s
        """, {'pid': portfolio_id}).fetchall()

        if not positions:
            raise HTTPException(status_code=404, detail="No positions found")

        stage_counts = {1: 0, 2: 0, 3: 0}
        position_stages = []

        for pos in positions:
            stage = stage_classification(
                current_pd=float(pos['current_pd']),
                origination_pd=float(pos['origination_pd']),
                days_past_due=int(pos['days_past_due']),
            )
            stage_counts[stage] += 1
            position_stages.append({
                'position_id': pos['position_id'],
                'stage': stage,
                'current_pd': float(pos['current_pd']),
                'origination_pd': float(pos['origination_pd']),
                'days_past_due': int(pos['days_past_due']),
            })

        return {
            'portfolio_id': portfolio_id,
            'stage_distribution': stage_counts,
            'total_positions': len(positions),
            'positions': position_stages,
        }


@router.post("/backtest/{run_id}")
def backtest_cecl(run_id: str):
    """Run a backtest comparing CECL predictions against actual losses."""
    raise HTTPException(status_code=501, detail="Backtesting not yet implemented")
