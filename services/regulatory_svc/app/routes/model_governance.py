"""Model governance versioning, backtesting, and calibration tracking."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.common.db import db_conn
from services.common.audit import log_audit_entry
from psycopg.rows import dict_row
from psycopg.types.json import Json

router = APIRouter()


class ModelVersionIn(BaseModel):
    model_version: str
    model_type: str
    git_hash: Optional[str] = None
    deployment_date: str
    approval_status: str = "TESTING"
    backtesting_results_json: Optional[Dict[str, Any]] = None
    calibration_date: Optional[str] = None
    calibration_params_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class ModelVersionOut(BaseModel):
    model_version: str
    model_type: str
    git_hash: Optional[str]
    deployment_date: str
    approval_status: str
    backtesting_results_json: Optional[Dict[str, Any]]
    calibration_date: Optional[str]
    notes: Optional[str]


@router.get("/", response_model=List[ModelVersionOut])
def list_models(model_type: Optional[str] = None):
    """List all model versions, optionally filtered by type."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        if model_type:
            rows = conn.execute("""
                SELECT model_version, model_type, git_hash, deployment_date,
                       approval_status, backtesting_results_json, calibration_date, notes
                FROM model_governance
                WHERE model_type = %(mt)s
                ORDER BY deployment_date DESC
            """, {'mt': model_type}).fetchall()
        else:
            rows = conn.execute("""
                SELECT model_version, model_type, git_hash, deployment_date,
                       approval_status, backtesting_results_json, calibration_date, notes
                FROM model_governance
                ORDER BY deployment_date DESC
            """).fetchall()

        return [
            ModelVersionOut(
                model_version=r['model_version'],
                model_type=r['model_type'],
                git_hash=r['git_hash'],
                deployment_date=str(r['deployment_date']),
                approval_status=r['approval_status'],
                backtesting_results_json=r['backtesting_results_json'],
                calibration_date=str(r['calibration_date']) if r['calibration_date'] else None,
                notes=r['notes'],
            )
            for r in rows
        ]


@router.post("/", response_model=ModelVersionOut, status_code=201)
def register_model(model: ModelVersionIn):
    """Register a new model version."""

    with db_conn() as conn:
        conn.execute("""
            INSERT INTO model_governance
              (model_version, model_type, git_hash, deployment_date, approval_status,
               backtesting_results_json, calibration_date, calibration_params_json, notes)
            VALUES (%(ver)s, %(type)s, %(hash)s, %(deploy)s::timestamptz, %(status)s,
                    %(back)s, %(cal)s::timestamptz, %(cal_params)s, %(notes)s)
        """, {
            'ver': model.model_version,
            'type': model.model_type,
            'hash': model.git_hash,
            'deploy': model.deployment_date,
            'status': model.approval_status,
            'back': Json(model.backtesting_results_json or {}),
            'cal': model.calibration_date,
            'cal_params': Json(model.calibration_params_json or {}),
            'notes': model.notes,
        })

    # Log model change to audit trail
    log_audit_entry(
        audit_type="MODEL_CHANGE",
        calculation_run_id=f"model-reg-{model.model_version}",
        entity_type="PORTFOLIO",
        entity_id="SYSTEM",
        calculation_method="MODEL_REGISTRATION",
        input_snapshot_id="N/A",
        assumptions={"model_version": model.model_version, "model_type": model.model_type},
        results={"approval_status": model.approval_status},
    )

    return ModelVersionOut(
        model_version=model.model_version,
        model_type=model.model_type,
        git_hash=model.git_hash,
        deployment_date=model.deployment_date,
        approval_status=model.approval_status,
        backtesting_results_json=model.backtesting_results_json,
        calibration_date=model.calibration_date,
        notes=model.notes,
    )


@router.patch("/{model_version}", response_model=ModelVersionOut)
def update_model_status(model_version: str, approval_status: str):
    """Update model approval status (TESTING -> APPROVED -> DEPRECATED)."""

    if approval_status not in ("TESTING", "APPROVED", "DEPRECATED"):
        raise HTTPException(status_code=400, detail="Invalid approval status")

    with db_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute("""
            UPDATE model_governance
            SET approval_status = %(status)s
            WHERE model_version = %(ver)s
            RETURNING model_version, model_type, git_hash, deployment_date,
                      approval_status, backtesting_results_json, calibration_date, notes
        """, {'ver': model_version, 'status': approval_status}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Model version not found")

        # Log status change
        log_audit_entry(
            audit_type="MODEL_CHANGE",
            calculation_run_id=f"model-status-{model_version}",
            entity_type="PORTFOLIO",
            entity_id="SYSTEM",
            calculation_method="STATUS_CHANGE",
            input_snapshot_id="N/A",
            assumptions={"model_version": model_version, "new_status": approval_status},
            results={"approval_status": approval_status},
        )

        return ModelVersionOut(
            model_version=row['model_version'],
            model_type=row['model_type'],
            git_hash=row['git_hash'],
            deployment_date=str(row['deployment_date']),
            approval_status=row['approval_status'],
            backtesting_results_json=row['backtesting_results_json'],
            calibration_date=str(row['calibration_date']) if row['calibration_date'] else None,
            notes=row['notes'],
        )


@router.get("/{model_version}", response_model=ModelVersionOut)
def get_model(model_version: str):
    """Get details for a specific model version."""

    with db_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute("""
            SELECT model_version, model_type, git_hash, deployment_date,
                   approval_status, backtesting_results_json, calibration_date, notes
            FROM model_governance
            WHERE model_version = %(ver)s
        """, {'ver': model_version}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Model version not found")

        return ModelVersionOut(
            model_version=row['model_version'],
            model_type=row['model_type'],
            git_hash=row['git_hash'],
            deployment_date=str(row['deployment_date']),
            approval_status=row['approval_status'],
            backtesting_results_json=row['backtesting_results_json'],
            calibration_date=str(row['calibration_date']) if row['calibration_date'] else None,
            notes=row['notes'],
        )
