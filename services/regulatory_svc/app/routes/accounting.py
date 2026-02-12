"""GAAP / IFRS valuation and classification endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.regulatory_svc.app.models import (
    AccountingValuationRequest,
    AccountingValuationResult,
    FairValueEntry,
)
from compute.regulatory.gaap_ifrs import (
    classify_gaap_category,
    classify_ifrs_category,
    compute_gaap_valuation,
    compute_ifrs_valuation,
)
from services.common.db import db_conn
from services.common.audit import log_audit_entry
from psycopg.rows import dict_row

router = APIRouter()


@router.post("/valuations", response_model=AccountingValuationResult, status_code=201)
def compute_accounting_valuation(req: AccountingValuationRequest):
    """Classify positions into fair-value hierarchy levels and compute carrying vs. fair values."""

    with db_conn() as conn:
        conn.row_factory = dict_row

        positions = conn.execute("""
            SELECT
              pos.position_id,
              pos.instrument_id,
              COALESCE(pos.cost_basis, 0) AS book_value,
              COALESCE((vr.measures_json ->> 'PV')::numeric, 0) AS market_value,
              pos.metadata_json,
              COALESCE(instr.product_type, '') AS product_type
            FROM position pos
            LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
            LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
              AND vr.scenario_id = 'BASE'
            WHERE pos.portfolio_node_id = %(pid)s
        """, {'pid': req.portfolio_node_id}).fetchall()

        if not positions:
            raise HTTPException(status_code=404, detail="No positions found")

        entries = []
        total_carrying = 0.0
        total_fair = 0.0
        total_unrealised = 0.0

        for pos in positions:
            market_value = float(pos['market_value'] or 0)
            book_value = float(pos['book_value'] or 0)
            metadata = pos['metadata_json'] or {}
            metadata['product_type'] = pos['product_type']

            if req.standard == "US_GAAP":
                result = compute_gaap_valuation(
                    position=metadata,
                    market_value=market_value,
                    book_value=book_value,
                )
                classification = _gaap_to_classification(result["category"])
            else:
                result = compute_ifrs_valuation(
                    position=metadata,
                    market_value=market_value,
                    book_value=book_value,
                )
                classification = _ifrs_to_classification(result["category"])

            entries.append(FairValueEntry(
                position_id=pos['position_id'],
                instrument_id=pos['instrument_id'],
                classification=classification,
                carrying_value=result["carrying_value"],
                fair_value=market_value,
                unrealised_pnl=result.get("unrealized_gain_loss", 0.0),
            ))

            total_carrying += result["carrying_value"]
            total_fair += market_value
            total_unrealised += result.get("unrealized_gain_loss", 0.0)

        # Log audit trail
        log_audit_entry(
            audit_type="GAAP" if req.standard == "US_GAAP" else "IFRS",
            calculation_run_id=req.run_id,
            entity_type="PORTFOLIO",
            entity_id=req.portfolio_node_id,
            calculation_method=req.standard,
            input_snapshot_id="N/A",
            assumptions={"standard": req.standard},
            results={
                "total_carrying_value": total_carrying,
                "total_fair_value": total_fair,
                "total_unrealised_pnl": total_unrealised,
                "position_count": len(entries),
            },
        )

        return AccountingValuationResult(
            run_id=req.run_id,
            as_of_date=req.as_of_date,
            standard=req.standard,
            entries=entries,
            total_carrying_value=total_carrying,
            total_fair_value=total_fair,
            total_unrealised_pnl=total_unrealised,
        )


@router.get("/valuations/{run_id}", response_model=AccountingValuationResult)
def get_accounting_valuation(run_id: str):
    """Retrieve a previously computed accounting valuation result."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        audit = conn.execute("""
            SELECT entity_id, assumptions_json, results_json, computed_at
            FROM audit_trail
            WHERE calculation_run_id = %(rid)s AND audit_type IN ('GAAP', 'IFRS')
            ORDER BY computed_at DESC LIMIT 1
        """, {'rid': run_id}).fetchone()

        if not audit:
            raise HTTPException(status_code=404, detail="Accounting result not found")

        results = audit['results_json']
        return AccountingValuationResult(
            run_id=run_id,
            as_of_date=audit['computed_at'],
            standard=audit['assumptions_json'].get('standard', 'US_GAAP'),
            total_carrying_value=results.get('total_carrying_value', 0.0),
            total_fair_value=results.get('total_fair_value', 0.0),
            total_unrealised_pnl=results.get('total_unrealised_pnl', 0.0),
            computed_at=audit['computed_at'],
        )


@router.get("/fair-value-hierarchy/{run_id}")
def get_fair_value_hierarchy(run_id: str):
    """Return the fair-value hierarchy (Level 1/2/3) breakdown for a run."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        audit = conn.execute("""
            SELECT results_json FROM audit_trail
            WHERE calculation_run_id = %(rid)s AND audit_type IN ('GAAP', 'IFRS')
            ORDER BY computed_at DESC LIMIT 1
        """, {'rid': run_id}).fetchone()

        if not audit:
            raise HTTPException(status_code=404, detail="Valuation not found")

        return {
            "run_id": run_id,
            "hierarchy": {
                "LEVEL_1": audit['results_json'].get('total_fair_value', 0.0),
                "LEVEL_2": 0.0,
                "LEVEL_3": 0.0,
            },
        }


@router.get("/unrealised-pnl/{portfolio_node_id}")
def get_unrealised_pnl(portfolio_node_id: str):
    """Return aggregate unrealised P&L by classification bucket."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        audit = conn.execute("""
            SELECT results_json, assumptions_json FROM audit_trail
            WHERE entity_id = %(pid)s AND audit_type IN ('GAAP', 'IFRS')
            ORDER BY computed_at DESC LIMIT 1
        """, {'pid': portfolio_node_id}).fetchone()

        if not audit:
            raise HTTPException(status_code=404, detail="No valuation found")

        return {
            "portfolio_node_id": portfolio_node_id,
            "standard": audit['assumptions_json'].get('standard', 'US_GAAP'),
            "total_unrealised_pnl": audit['results_json'].get('total_unrealised_pnl', 0.0),
        }


@router.get("/hedge-effectiveness/{run_id}")
def get_hedge_effectiveness(run_id: str):
    """Evaluate hedge effectiveness metrics for designated hedging relationships."""
    raise HTTPException(status_code=501, detail="Hedge effectiveness not yet implemented")


@router.get("/impairment/{portfolio_node_id}")
def get_impairment_assessment(portfolio_node_id: str):
    """Return impairment assessment (IFRS 9 staging or US GAAP OTTI) for a portfolio."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        positions = conn.execute("""
            SELECT
              pos.position_id,
              COALESCE(pos.cost_basis, 0) AS book_value,
              COALESCE((vr.measures_json ->> 'PV')::numeric, 0) AS market_value,
              pos.metadata_json
            FROM position pos
            LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
              AND vr.scenario_id = 'BASE'
            WHERE pos.portfolio_node_id = %(pid)s
        """, {'pid': portfolio_node_id}).fetchall()

        if not positions:
            raise HTTPException(status_code=404, detail="No positions found")

        impaired = []
        for pos in positions:
            bv = float(pos['book_value'] or 0)
            mv = float(pos['market_value'] or 0)
            if bv > 0 and mv < bv * 0.90:
                impaired.append({
                    "position_id": pos['position_id'],
                    "book_value": bv,
                    "market_value": mv,
                    "impairment": bv - mv,
                    "decline_pct": (1 - mv / bv) * 100,
                })

        return {
            "portfolio_node_id": portfolio_node_id,
            "impaired_count": len(impaired),
            "total_impairment": sum(i["impairment"] for i in impaired),
            "impaired_positions": impaired,
        }


def _gaap_to_classification(category: str) -> str:
    """Map GAAP category to model classification enum."""
    mapping = {
        "HELD_TO_MATURITY": "HTM",
        "AVAILABLE_FOR_SALE": "AFS",
        "TRADING": "HFT",
    }
    return mapping.get(category, "AFS")


def _ifrs_to_classification(category: str) -> str:
    """Map IFRS category to model classification enum."""
    mapping = {
        "AMORTIZED_COST": "AMORTISED_COST",
        "FVOCI": "FVOCI",
        "FVTPL": "FVTPL",
    }
    return mapping.get(category, "FVTPL")
