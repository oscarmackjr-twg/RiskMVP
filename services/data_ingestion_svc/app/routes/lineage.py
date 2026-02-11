"""Data lineage tracking endpoints."""
from __future__ import annotations

from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException

from services.common.db import db_conn
from services.data_ingestion_svc.app.models import (
    LineageOut,
    LineageGraphOut,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
)

router = APIRouter()


@router.get("/feed/{feed_id}", response_model=list[LineageOut])
def get_lineage_for_feed(feed_id: str):
    """Get lineage for specific feed."""
    with db_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM data_lineage
            WHERE feed_id = %(fid)s
            ORDER BY ingested_at DESC
        """, {"fid": feed_id}).fetchall()

        if not rows:
            return []

        return [
            LineageOut(
                lineage_id=row["lineage_id"],
                feed_type=row["feed_type"],
                feed_id=row["feed_id"],
                source_system=row["source_system"],
                source_identifier=row["source_identifier"],
                ingested_at=row["ingested_at"],
                transformation_chain=row["transformation_chain"],
                quality_checks_passed=row["quality_checks_passed"],
                metadata_json=row["metadata_json"]
            )
            for row in rows
        ]


@router.get("/position/{position_id}", response_model=LineageGraphOut)
def trace_position_lineage(position_id: str):
    """Trace position lineage back to all contributing feeds."""
    with db_conn() as conn:
        # Get position details
        pos_rows = conn.execute("""
            SELECT p.*, i.instrument_type
            FROM position p
            JOIN instrument i ON p.instrument_id = i.instrument_id
            WHERE p.position_id = %(pid)s
        """, {"pid": position_id}).fetchall()

        if not pos_rows:
            raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")

        pos = pos_rows[0]
        nodes = []
        edges = []

        # Add position node
        nodes.append({
            "id": position_id,
            "type": "position",
            "label": f"Position: {pos['instrument_id']}",
            "metadata": {
                "portfolio_node_id": pos["portfolio_node_id"],
                "quantity": float(pos["quantity"]),
                "base_ccy": pos["base_ccy"]
            }
        })

        # Find servicing batch that created/updated this position
        lineage_rows = conn.execute("""
            SELECT * FROM data_lineage
            WHERE feed_type = 'LOAN_SERVICING'
              AND metadata_json->>'batch_id' IS NOT NULL
            ORDER BY ingested_at DESC
            LIMIT 10
        """, {}).fetchall()

        for lineage in lineage_rows:
            batch_id = lineage["metadata_json"].get("batch_id") if lineage["metadata_json"] else None
            if batch_id:
                nodes.append({
                    "id": batch_id,
                    "type": "batch",
                    "label": f"Batch: {batch_id}",
                    "metadata": {
                        "source_file": lineage["metadata_json"].get("source_file"),
                        "ingested_at": lineage["ingested_at"].isoformat()
                    }
                })
                edges.append({
                    "source": batch_id,
                    "target": position_id,
                    "relationship": "CREATES"
                })

        # Find market data feeds (via runs if they exist)
        run_rows = conn.execute("""
            SELECT DISTINCT r.run_id, r.marketdata_snapshot_id
            FROM run r
            JOIN valuation_result vr ON vr.run_id = r.run_id
            WHERE vr.position_id = %(pid)s
            LIMIT 5
        """, {"pid": position_id}).fetchall()

        for run in run_rows:
            snapshot_id = run["marketdata_snapshot_id"]
            if snapshot_id:
                # Find FX spots for this snapshot
                fx_lineage = conn.execute("""
                    SELECT * FROM data_lineage
                    WHERE feed_type = 'FX_SPOT' AND feed_id = %(sid)s
                """, {"sid": snapshot_id}).fetchall()

                for fx in fx_lineage:
                    node_id = f"fx-{snapshot_id}"
                    if not any(n["id"] == node_id for n in nodes):
                        nodes.append({
                            "id": node_id,
                            "type": "fx_spot",
                            "label": f"FX Spots: {snapshot_id}",
                            "metadata": {
                                "source_system": fx["source_system"],
                                "ingested_at": fx["ingested_at"].isoformat()
                            }
                        })
                        edges.append({
                            "source": node_id,
                            "target": position_id,
                            "relationship": "PRICES"
                        })

        return LineageGraphOut(nodes=nodes, edges=edges)


@router.post("/impact-analysis", response_model=ImpactAnalysisResponse)
def analyze_feed_impact(req: ImpactAnalysisRequest):
    """Impact analysis for feed - identify affected runs and positions."""
    with db_conn() as conn:
        affected_runs = []
        affected_positions = []

        # Find lineage record for this feed
        lineage_rows = conn.execute("""
            SELECT * FROM data_lineage
            WHERE feed_id = %(fid)s
            LIMIT 1
        """, {"fid": req.feed_id}).fetchall()

        if not lineage_rows:
            return ImpactAnalysisResponse(
                affected_runs=[],
                affected_positions=[]
            )

        lineage = lineage_rows[0]
        feed_type = lineage["feed_type"]

        # If FX_SPOT, find runs using this snapshot
        if feed_type == "FX_SPOT":
            run_rows = conn.execute("""
                SELECT run_id FROM run
                WHERE marketdata_snapshot_id = %(sid)s
            """, {"sid": req.feed_id}).fetchall()
            affected_runs = [row["run_id"] for row in run_rows]

            # Find positions in these runs
            if affected_runs:
                pos_rows = conn.execute("""
                    SELECT DISTINCT position_id
                    FROM valuation_result
                    WHERE run_id = ANY(%(rids)s)
                """, {"rids": affected_runs}).fetchall()
                affected_positions = [row["position_id"] for row in pos_rows]

        # If YIELD_CURVE or CREDIT_SPREAD, find runs using market data
        elif feed_type in ("YIELD_CURVE", "CREDIT_SPREAD"):
            # Market data impacts all runs since a specific as_of_date
            # For now, return empty (would need market_data_snapshot payload inspection)
            pass

        # If RATING, find positions with this issuer
        elif feed_type == "RATING":
            entity_id = lineage.get("source_identifier")
            if entity_id:
                # Find instruments with this issuer
                inst_rows = conn.execute("""
                    SELECT instrument_id FROM instrument
                    WHERE payload_json->>'issuer_id' = %(eid)s
                """, {"eid": entity_id}).fetchall()

                if inst_rows:
                    instrument_ids = [row["instrument_id"] for row in inst_rows]
                    pos_rows = conn.execute("""
                        SELECT position_id FROM position
                        WHERE instrument_id = ANY(%(iids)s) AND status = 'ACTIVE'
                    """, {"iids": instrument_ids}).fetchall()
                    affected_positions = [row["position_id"] for row in pos_rows]

        return ImpactAnalysisResponse(
            affected_runs=affected_runs,
            affected_positions=affected_positions
        )


@router.get("/graph", response_model=LineageGraphOut)
def get_lineage_graph(
    feed_type: str | None = None,
    source_system: str | None = None,
    limit: int = 50
):
    """Get full lineage graph with optional filters."""
    with db_conn() as conn:
        # Build WHERE clause
        where_clauses = []
        params = {"lim": limit}

        if feed_type:
            where_clauses.append("feed_type = %(ft)s")
            params["ft"] = feed_type

        if source_system:
            where_clauses.append("source_system = %(ss)s")
            params["ss"] = source_system

        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

        rows = conn.execute(f"""
            SELECT * FROM data_lineage
            WHERE {where_sql}
            ORDER BY ingested_at DESC
            LIMIT %(lim)s
        """, params).fetchall()

        nodes = []
        edges = []

        for row in rows:
            # Add feed node
            feed_node_id = row["feed_id"] or row["lineage_id"]
            nodes.append({
                "id": feed_node_id,
                "type": row["feed_type"],
                "label": f"{row['feed_type']}: {feed_node_id}",
                "metadata": {
                    "source_system": row["source_system"],
                    "ingested_at": row["ingested_at"].isoformat(),
                    "quality_passed": row["quality_checks_passed"]
                }
            })

            # Add transformation nodes
            for i, transform in enumerate(row["transformation_chain"]):
                transform_id = f"{feed_node_id}-{transform}-{i}"
                nodes.append({
                    "id": transform_id,
                    "type": "transformation",
                    "label": transform,
                    "metadata": {}
                })

                if i == 0:
                    edges.append({
                        "source": feed_node_id,
                        "target": transform_id,
                        "relationship": "FEEDS_INTO"
                    })
                else:
                    prev_transform_id = f"{feed_node_id}-{row['transformation_chain'][i-1]}-{i-1}"
                    edges.append({
                        "source": prev_transform_id,
                        "target": transform_id,
                        "relationship": "TRANSFORMS"
                    })

        return LineageGraphOut(nodes=nodes, edges=edges)


@router.get("/quality-checks", response_model=list[LineageOut])
def list_quality_check_failures():
    """List quality check failures."""
    with db_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM data_lineage
            WHERE quality_checks_passed = false
            ORDER BY ingested_at DESC
            LIMIT 100
        """, {}).fetchall()

        return [
            LineageOut(
                lineage_id=row["lineage_id"],
                feed_type=row["feed_type"],
                feed_id=row["feed_id"],
                source_system=row["source_system"],
                source_identifier=row["source_identifier"],
                ingested_at=row["ingested_at"],
                transformation_chain=row["transformation_chain"],
                quality_checks_passed=row["quality_checks_passed"],
                metadata_json=row["metadata_json"]
            )
            for row in rows
        ]
