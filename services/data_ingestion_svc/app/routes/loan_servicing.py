"""Loan servicing data ingestion endpoints."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from psycopg.types.json import Json

from services.common.db import db_conn
from services.data_ingestion_svc.app.models import (
    LoanServicingBatch,
    IngestionBatchStatus,
    ReconcileRequest,
    ReconcileResponse,
)

router = APIRouter()


@router.post("/batch", response_model=IngestionBatchStatus, status_code=201)
def ingest_loan_servicing_batch(req: LoanServicingBatch):
    """Ingest a batch of loan servicing positions with validation."""
    batch_id = f"batch-{uuid4()}"
    validation_errors = []

    # Validate positions
    with db_conn() as conn:
        for idx, pos in enumerate(req.positions):
            # Validate instrument_id exists
            inst_rows = conn.execute(
                "SELECT 1 FROM instrument WHERE instrument_id = %(iid)s",
                {"iid": pos.instrument_id}
            ).fetchall()
            if not inst_rows:
                validation_errors.append(
                    f"Position {idx}: instrument_id '{pos.instrument_id}' not found"
                )

            # Validate portfolio_node_id exists
            node_rows = conn.execute(
                "SELECT 1 FROM portfolio_node WHERE portfolio_node_id = %(pnid)s",
                {"pnid": pos.portfolio_node_id}
            ).fetchall()
            if not node_rows:
                validation_errors.append(
                    f"Position {idx}: portfolio_node_id '{pos.portfolio_node_id}' not found"
                )

            # Validate values
            if pos.quantity <= 0:
                validation_errors.append(
                    f"Position {idx}: quantity must be > 0, got {pos.quantity}"
                )
            if pos.cost_basis < 0:
                validation_errors.append(
                    f"Position {idx}: cost_basis must be >= 0, got {pos.cost_basis}"
                )
            if pos.book_value < 0:
                validation_errors.append(
                    f"Position {idx}: book_value must be >= 0, got {pos.book_value}"
                )

            # Validate currency (simple 3-letter check)
            if len(pos.base_ccy) != 3 or not pos.base_ccy.isupper():
                validation_errors.append(
                    f"Position {idx}: base_ccy must be 3-letter uppercase code, got '{pos.base_ccy}'"
                )

        # Determine status
        status = 'COMPLETED' if not validation_errors else 'FAILED'

        # Insert into ingestion_batch
        conn.execute("""
            INSERT INTO ingestion_batch
              (batch_id, batch_type, source_file, record_count, validation_errors_json,
               status, started_at, completed_at, created_by)
            VALUES (%(bid)s, 'LOAN_SERVICING', %(sf)s, %(rc)s, %(ve)s::jsonb,
                    %(st)s, now(), now(), 'system')
        """, {
            "bid": batch_id,
            "sf": req.source_file,
            "rc": len(req.positions),
            "ve": Json(validation_errors) if validation_errors else Json([]),
            "st": status
        })

        # If validation passed, UPSERT positions
        if not validation_errors:
            for pos in req.positions:
                position_id = f"{pos.portfolio_node_id}-{pos.instrument_id}"
                conn.execute("""
                    INSERT INTO position
                      (position_id, portfolio_node_id, instrument_id, quantity, base_ccy,
                       cost_basis, book_value, status, created_at, updated_at)
                    VALUES (%(pid)s, %(pnid)s, %(iid)s, %(qty)s, %(ccy)s, %(cb)s, %(bv)s, 'ACTIVE', now(), now())
                    ON CONFLICT (portfolio_node_id, instrument_id)
                    DO UPDATE SET
                      quantity = EXCLUDED.quantity,
                      cost_basis = EXCLUDED.cost_basis,
                      book_value = EXCLUDED.book_value,
                      updated_at = now()
                """, {
                    "pid": position_id,
                    "pnid": pos.portfolio_node_id,
                    "iid": pos.instrument_id,
                    "qty": pos.quantity,
                    "ccy": pos.base_ccy,
                    "cb": pos.cost_basis,
                    "bv": pos.book_value
                })

            # Record lineage
            lineage_id = f"batch-{batch_id}-{datetime.utcnow().isoformat()}"
            metadata_json = {
                "batch_id": batch_id,
                "record_count": len(req.positions),
                "source_file": req.source_file
            }
            conn.execute("""
                INSERT INTO data_lineage
                  (lineage_id, feed_type, feed_id, source_system, source_identifier,
                   ingested_at, transformation_chain, quality_checks_passed, metadata_json)
                VALUES (%(lid)s, 'LOAN_SERVICING', %(bid)s, 'LOAN_SERVICING', %(sf)s,
                        now(), %(tc)s, true, %(meta)s::jsonb)
            """, {
                "lid": lineage_id,
                "bid": batch_id,
                "sf": req.source_file,
                "tc": ['RECEIVE', 'VALIDATE', 'PARSE', 'UPSERT'],
                "meta": Json(metadata_json)
            })

    return IngestionBatchStatus(
        batch_id=batch_id,
        status=status,
        record_count=len(req.positions),
        validation_errors=validation_errors,
        ingested_at=datetime.utcnow()
    )


@router.get("/batch/{batch_id}", response_model=IngestionBatchStatus)
def get_batch_status(batch_id: str):
    """Check the validation and ingestion status of a loan servicing batch."""
    with db_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM ingestion_batch WHERE batch_id = %(bid)s
        """, {"bid": batch_id}).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail=f"Batch not found: {batch_id}")

        row = rows[0]
        return IngestionBatchStatus(
            batch_id=row["batch_id"],
            status=row["status"],
            record_count=row["record_count"],
            validation_errors=row["validation_errors_json"] or [],
            ingested_at=row["started_at"]
        )


@router.get("/batches", response_model=list[IngestionBatchStatus])
def list_batches(status: str | None = None, limit: int = 50):
    """List loan servicing batch ingestion jobs with optional status filter."""
    with db_conn() as conn:
        if status:
            rows = conn.execute("""
                SELECT * FROM ingestion_batch
                WHERE batch_type = 'LOAN_SERVICING' AND status = %(st)s
                ORDER BY started_at DESC
                LIMIT %(lim)s
            """, {"st": status, "lim": limit}).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM ingestion_batch
                WHERE batch_type = 'LOAN_SERVICING'
                ORDER BY started_at DESC
                LIMIT %(lim)s
            """, {"lim": limit}).fetchall()

        return [
            IngestionBatchStatus(
                batch_id=row["batch_id"],
                status=row["status"],
                record_count=row["record_count"],
                validation_errors=row["validation_errors_json"] or [],
                ingested_at=row["started_at"]
            )
            for row in rows
        ]


@router.post("/reconcile", response_model=ReconcileResponse)
def reconcile_positions(req: ReconcileRequest):
    """Reconcile positions against servicing file."""
    with db_conn() as conn:
        # Query actual positions
        rows = conn.execute("""
            SELECT instrument_id, quantity
            FROM position
            WHERE portfolio_node_id = %(pid)s AND status = 'ACTIVE'
        """, {"pid": req.portfolio_node_id}).fetchall()

        actual_positions = {row["instrument_id"]: float(row["quantity"]) for row in rows}
        expected_positions = {pos.instrument_id: pos.quantity for pos in req.expected_positions}

        # Compare
        missing = []
        extra = []
        mismatches = []

        # Find missing positions (in expected, not in actual)
        for inst_id in expected_positions:
            if inst_id not in actual_positions:
                missing.append(inst_id)

        # Find extra positions (in actual, not in expected)
        for inst_id in actual_positions:
            if inst_id not in expected_positions:
                extra.append(inst_id)

        # Find mismatches (different quantity)
        for inst_id in expected_positions:
            if inst_id in actual_positions:
                if abs(expected_positions[inst_id] - actual_positions[inst_id]) > 0.01:
                    mismatches.append({
                        "instrument_id": inst_id,
                        "expected_quantity": expected_positions[inst_id],
                        "actual_quantity": actual_positions[inst_id],
                        "difference": expected_positions[inst_id] - actual_positions[inst_id]
                    })

        match_count = len([
            inst_id for inst_id in expected_positions
            if inst_id in actual_positions and abs(expected_positions[inst_id] - actual_positions[inst_id]) <= 0.01
        ])

        return ReconcileResponse(
            missing=missing,
            extra=extra,
            mismatches=mismatches,
            match_count=match_count,
            total_count=len(expected_positions)
        )
