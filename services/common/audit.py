"""Shared audit trail logging for regulatory calculations."""
from __future__ import annotations

from typing import Dict, Any
from uuid import uuid4
from datetime import datetime, timezone

from services.common.db import db_conn
from psycopg.types.json import Json


def log_audit_entry(
    audit_type: str,
    calculation_run_id: str,
    entity_type: str,
    entity_id: str,
    calculation_method: str,
    input_snapshot_id: str,
    assumptions: Dict[str, Any],
    results: Dict[str, Any],
) -> str:
    """Log immutable audit entry. Returns audit_id.

    Args:
        audit_type: One of GAAP, IFRS, CECL, BASEL, MODEL_CHANGE
        calculation_run_id: Unique run identifier
        entity_type: POSITION, PORTFOLIO, or COUNTERPARTY
        entity_id: Entity being audited
        calculation_method: Algorithm used
        input_snapshot_id: Market data snapshot
        assumptions: Input assumptions as JSON
        results: Calculation results as JSON

    Returns:
        The generated audit_id string
    """
    audit_id = str(uuid4())

    with db_conn() as conn:
        conn.execute("""
            INSERT INTO audit_trail
              (audit_id, audit_type, calculation_run_id, entity_type, entity_id,
               calculation_method, input_snapshot_id, input_version, assumptions_json,
               results_json, metadata_json, computed_at)
            VALUES (%(aid)s, %(at)s, %(crid)s, %(et)s, %(eid)s,
                    %(cm)s, %(snap)s, %(ver)s, %(assum)s,
                    %(res)s, %(meta)s, now())
        """, {
            'aid': audit_id,
            'at': audit_type,
            'crid': calculation_run_id,
            'et': entity_type,
            'eid': entity_id,
            'cm': calculation_method,
            'snap': input_snapshot_id,
            'ver': 'v1.0.0',
            'assum': Json(assumptions),
            'res': Json(results),
            'meta': Json({
                'computed_by': 'regulatory_svc',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            })
        })

    return audit_id
