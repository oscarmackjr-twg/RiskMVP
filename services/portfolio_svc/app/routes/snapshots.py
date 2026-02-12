"""Historical snapshots and time-series endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from services.portfolio_svc.app.models import (
    SnapshotCreate,
    SnapshotOut,
    SnapshotCompareRequest,
    SnapshotCompareResponse,
    SnapshotTimeSeriesPoint,
    PositionChange,
    PortfolioSnapshotCreate,
    PortfolioSnapshotOut,
    TimeSeriesResponse,
)
from services.common.db import db_conn
from services.common.hash import sha256_json

router = APIRouter()


# ---------------------------------------------------------------------------
# New snapshot endpoints (Plan 03-05)
# ---------------------------------------------------------------------------

@router.post("", response_model=SnapshotOut, status_code=201)
def create_snapshot(req: SnapshotCreate):
    """Create a point-in-time portfolio snapshot with deduplication."""

    # Build query to aggregate current positions
    if req.include_hierarchy:
        # Recursive query including child portfolios
        positions_query = """
        WITH RECURSIVE hierarchy AS (
          SELECT portfolio_node_id FROM portfolio_node
          WHERE portfolio_node_id = %(pid)s
          UNION ALL
          SELECT pn.portfolio_node_id
          FROM portfolio_node pn
          INNER JOIN hierarchy h ON pn.parent_id = h.portfolio_node_id
        )
        SELECT
          instrument_id,
          product_type,
          base_ccy,
          SUM(quantity) AS aggregated_quantity,
          COUNT(DISTINCT position_id) AS position_count
        FROM position
        WHERE portfolio_node_id IN (SELECT portfolio_node_id FROM hierarchy)
          AND status = 'ACTIVE'
        GROUP BY instrument_id, product_type, base_ccy
        ORDER BY instrument_id;
        """
    else:
        # Single portfolio query
        positions_query = """
        SELECT
          instrument_id,
          product_type,
          base_ccy,
          SUM(quantity) AS aggregated_quantity,
          COUNT(DISTINCT position_id) AS position_count
        FROM position
        WHERE portfolio_node_id = %(pid)s AND status = 'ACTIVE'
        GROUP BY instrument_id, product_type, base_ccy
        ORDER BY instrument_id;
        """

    with db_conn() as conn:
        # Get position aggregations
        params = {"pid": req.portfolio_node_id}
        rows = conn.execute(positions_query, params).fetchall()

        # Build payload
        positions = [
            {
                "instrument_id": row["instrument_id"],
                "product_type": row["product_type"],
                "base_ccy": row["base_ccy"],
                "aggregated_quantity": float(row["aggregated_quantity"]),
                "position_count": row["position_count"],
            }
            for row in rows
        ]

        payload_json = {
            "portfolio_node_id": req.portfolio_node_id,
            "as_of_date": req.as_of_date.isoformat(),
            "include_hierarchy": req.include_hierarchy,
            "positions": positions,
            "total_positions": sum(p["position_count"] for p in positions),
            "total_instruments": len(positions),
        }

        # Compute content-addressable hash
        payload_hash = sha256_json(payload_json)

        # Check for existing snapshot with same hash (deduplication)
        existing = conn.execute(
            """SELECT snapshot_id, created_at FROM portfolio_snapshot
               WHERE portfolio_node_id = %(pid)s AND payload_hash = %(ph)s""",
            {"pid": req.portfolio_node_id, "ph": payload_hash}
        ).fetchone()

        if existing:
            # Return existing snapshot (idempotent)
            return SnapshotOut(
                snapshot_id=existing["snapshot_id"],
                portfolio_node_id=req.portfolio_node_id,
                as_of_date=req.as_of_date,
                total_positions=payload_json["total_positions"],
                total_instruments=payload_json["total_instruments"],
                payload_json=payload_json,
                created_at=existing["created_at"],
            )

        # Create new snapshot
        # snapshot_id = snap-{portfolio_node_id}-{YYYYMMDD}-{short_hash}
        short_hash = payload_hash.split(":")[1][:8]
        date_str = req.as_of_date.strftime("%Y%m%d")
        snapshot_id = f"snap-{req.portfolio_node_id}-{date_str}-{short_hash}"

        # Insert snapshot
        conn.execute(
            """INSERT INTO portfolio_snapshot
               (snapshot_id, portfolio_node_id, as_of_date, payload_json, payload_hash, created_at)
               VALUES (%(sid)s, %(pid)s, %(aof)s, %(pl)s::jsonb, %(ph)s, now())
               ON CONFLICT (snapshot_id) DO UPDATE SET
                 payload_json = EXCLUDED.payload_json,
                 payload_hash = EXCLUDED.payload_hash""",
            {
                "sid": snapshot_id,
                "pid": req.portfolio_node_id,
                "aof": req.as_of_date,
                "pl": payload_json,
                "ph": payload_hash,
            }
        )
        conn.commit()

        # Fetch created snapshot
        created = conn.execute(
            "SELECT created_at FROM portfolio_snapshot WHERE snapshot_id = %(sid)s",
            {"sid": snapshot_id}
        ).fetchone()

        return SnapshotOut(
            snapshot_id=snapshot_id,
            portfolio_node_id=req.portfolio_node_id,
            as_of_date=req.as_of_date,
            total_positions=payload_json["total_positions"],
            total_instruments=payload_json["total_instruments"],
            payload_json=payload_json,
            created_at=created["created_at"],
        )


@router.get("/{snapshot_id}", response_model=SnapshotOut)
def get_snapshot(snapshot_id: str):
    """Get a single snapshot by ID with full payload."""
    with db_conn() as conn:
        row = conn.execute(
            """SELECT * FROM portfolio_snapshot WHERE snapshot_id = %(sid)s""",
            {"sid": snapshot_id}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")

        payload = row["payload_json"]
        return SnapshotOut(
            snapshot_id=row["snapshot_id"],
            portfolio_node_id=row["portfolio_node_id"],
            as_of_date=row["as_of_date"],
            total_positions=payload.get("total_positions", 0),
            total_instruments=payload.get("total_instruments", 0),
            payload_json=payload,
            created_at=row["created_at"],
        )


@router.get("", response_model=List[SnapshotOut])
def list_snapshots(
    portfolio_node_id: Optional[str] = Query(None, description="Filter by portfolio"),
    date_from: Optional[datetime] = Query(None, description="From date"),
    date_to: Optional[datetime] = Query(None, description="To date"),
    limit: int = Query(100, le=1000, description="Max results"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """List portfolio snapshots with filtering and pagination."""
    query = """
    SELECT * FROM portfolio_snapshot
    WHERE (%(pid)s IS NULL OR portfolio_node_id = %(pid)s)
      AND (%(from)s IS NULL OR as_of_date >= %(from)s)
      AND (%(to)s IS NULL OR as_of_date <= %(to)s)
    ORDER BY as_of_date DESC
    LIMIT %(lim)s OFFSET %(off)s
    """

    params = {
        "pid": portfolio_node_id,
        "from": date_from,
        "to": date_to,
        "lim": limit,
        "off": offset,
    }

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        return [
            SnapshotOut(
                snapshot_id=row["snapshot_id"],
                portfolio_node_id=row["portfolio_node_id"],
                as_of_date=row["as_of_date"],
                total_positions=row["payload_json"].get("total_positions", 0),
                total_instruments=row["payload_json"].get("total_instruments", 0),
                created_at=row["created_at"],
            )
            for row in rows
        ]


@router.post("/compare", response_model=SnapshotCompareResponse)
def compare_snapshots(req: SnapshotCompareRequest):
    """Compare two snapshots and identify position changes."""
    with db_conn() as conn:
        # Load both snapshots
        snap1 = conn.execute(
            "SELECT payload_json FROM portfolio_snapshot WHERE snapshot_id = %(sid)s",
            {"sid": req.snapshot_id_1}
        ).fetchone()

        snap2 = conn.execute(
            "SELECT payload_json FROM portfolio_snapshot WHERE snapshot_id = %(sid)s",
            {"sid": req.snapshot_id_2}
        ).fetchone()

        if not snap1:
            raise HTTPException(status_code=404, detail=f"Snapshot {req.snapshot_id_1} not found")
        if not snap2:
            raise HTTPException(status_code=404, detail=f"Snapshot {req.snapshot_id_2} not found")

        positions1 = {p["instrument_id"]: p for p in snap1["payload_json"]["positions"]}
        positions2 = {p["instrument_id"]: p for p in snap2["payload_json"]["positions"]}

        # Find new positions
        new_positions = [
            positions2[iid] for iid in positions2
            if iid not in positions1
        ]

        # Find removed positions
        removed_positions = [
            positions1[iid] for iid in positions1
            if iid not in positions2
        ]

        # Find quantity changes
        quantity_changes = []
        for iid in positions1:
            if iid in positions2:
                old_qty = positions1[iid]["aggregated_quantity"]
                new_qty = positions2[iid]["aggregated_quantity"]
                if old_qty != new_qty:
                    quantity_changes.append(
                        PositionChange(
                            instrument_id=iid,
                            product_type=positions2[iid]["product_type"],
                            base_ccy=positions2[iid]["base_ccy"],
                            old_quantity=old_qty,
                            new_quantity=new_qty,
                            quantity_change=new_qty - old_qty,
                        )
                    )

        # Build summary
        summary = {
            "new_count": len(new_positions),
            "removed_count": len(removed_positions),
            "changed_count": len(quantity_changes),
            "unchanged_count": len([iid for iid in positions1 if iid in positions2 and positions1[iid]["aggregated_quantity"] == positions2[iid]["aggregated_quantity"]]),
        }

        return SnapshotCompareResponse(
            snapshot_id_1=req.snapshot_id_1,
            snapshot_id_2=req.snapshot_id_2,
            new_positions=new_positions,
            removed_positions=removed_positions,
            quantity_changes=quantity_changes,
            summary=summary,
        )


@router.get("/{portfolio_id}/time-series", response_model=List[SnapshotTimeSeriesPoint])
def get_snapshot_timeseries(
    portfolio_id: str,
    date_from: Optional[datetime] = Query(None, description="From date"),
    date_to: Optional[datetime] = Query(None, description="To date"),
):
    """Get time-series of snapshots for a portfolio."""
    query = """
    SELECT
      snapshot_id,
      as_of_date,
      (payload_json ->> 'total_positions')::int AS position_count,
      (payload_json ->> 'total_instruments')::int AS instrument_count
    FROM portfolio_snapshot
    WHERE portfolio_node_id = %(pid)s
      AND (%(from)s IS NULL OR as_of_date >= %(from)s)
      AND (%(to)s IS NULL OR as_of_date <= %(to)s)
    ORDER BY as_of_date ASC
    """

    params = {
        "pid": portfolio_id,
        "from": date_from,
        "to": date_to,
    }

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()

        return [
            SnapshotTimeSeriesPoint(
                as_of_date=row["as_of_date"],
                position_count=row["position_count"],
                instrument_count=row["instrument_count"],
            )
            for row in rows
        ]


@router.delete("/{snapshot_id}", status_code=204)
def delete_snapshot(snapshot_id: str):
    """Delete a portfolio snapshot (hard delete for now)."""
    with db_conn() as conn:
        result = conn.execute(
            "DELETE FROM portfolio_snapshot WHERE snapshot_id = %(sid)s",
            {"sid": snapshot_id}
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")

        conn.commit()

    return None


# ---------------------------------------------------------------------------
# Legacy snapshot endpoints (backward compatibility)
# ---------------------------------------------------------------------------

@router.get("/legacy", response_model=List[PortfolioSnapshotOut])
def list_legacy_snapshots(
    portfolio_id: Optional[str] = Query(None, description="Filter by portfolio"),
    snapshot_type: Optional[str] = Query(None, description="Filter by snapshot type"),
):
    """List portfolio snapshots with optional filters (legacy)."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{snapshot_id}/positions")
def get_snapshot_positions(snapshot_id: str):
    """Get the frozen positions from a historical snapshot."""
    with db_conn() as conn:
        row = conn.execute(
            "SELECT payload_json FROM portfolio_snapshot WHERE snapshot_id = %(sid)s",
            {"sid": snapshot_id}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")

        return {"positions": row["payload_json"]["positions"]}


@router.get("/portfolio/{portfolio_id}/latest", response_model=SnapshotOut)
def get_latest_snapshot(portfolio_id: str):
    """Get the most recent snapshot for a portfolio."""
    with db_conn() as conn:
        row = conn.execute(
            """SELECT * FROM portfolio_snapshot
               WHERE portfolio_node_id = %(pid)s
               ORDER BY as_of_date DESC
               LIMIT 1""",
            {"pid": portfolio_id}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"No snapshots found for portfolio {portfolio_id}")

        payload = row["payload_json"]
        return SnapshotOut(
            snapshot_id=row["snapshot_id"],
            portfolio_node_id=row["portfolio_node_id"],
            as_of_date=row["as_of_date"],
            total_positions=payload.get("total_positions", 0),
            total_instruments=payload.get("total_instruments", 0),
            payload_json=payload,
            created_at=row["created_at"],
        )


@router.get("/portfolio/{portfolio_id}/timeseries", response_model=TimeSeriesResponse)
def get_timeseries(
    portfolio_id: str,
    measure: str = Query("market_value", description="Measure to chart over time"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
):
    """Get a time-series of a portfolio measure across historical snapshots."""
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/portfolio/{portfolio_id}/diff")
def diff_snapshots(
    portfolio_id: str,
    snapshot_id_a: str = Query(..., description="First snapshot ID"),
    snapshot_id_b: str = Query(..., description="Second snapshot ID"),
):
    """Compare two snapshots and return the difference in holdings."""
    raise HTTPException(status_code=501, detail="Not implemented")
