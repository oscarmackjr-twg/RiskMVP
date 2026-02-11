"""Instrument master CRUD endpoints."""
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime

from services.common.db import db_conn
from services.common.errors import NotFoundError

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class InstrumentCreate(BaseModel):
    """Request body to create a new instrument."""
    instrument_type: str = Field(..., description="Instrument type enum")
    terms_json: dict = Field(default_factory=dict, description="Instrument terms and characteristics")
    tags_json: dict = Field(default_factory=dict, description="Tags for filtering")


class InstrumentUpdate(BaseModel):
    """Partial update for an instrument (creates new version)."""
    terms_json: dict = Field(..., description="Updated terms")


class InstrumentOut(BaseModel):
    """Response model for a single instrument."""
    instrument_id: str
    instrument_type: str
    version: int
    terms_json: dict
    status: str = "APPROVED"
    created_at: Optional[datetime] = None


class InstrumentVersionOut(BaseModel):
    """Response model for instrument version history."""
    instrument_id: str
    version: int
    terms_json: dict
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BulkInstrumentCreate(BaseModel):
    """Request body for bulk instrument creation."""
    instruments: List[InstrumentCreate]


class BulkCreateResult(BaseModel):
    """Response for bulk creation."""
    created_count: int
    errors: List[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

VALID_INSTRUMENT_TYPES = {
    'LOAN', 'FIXED_BOND', 'FLOATING_BOND', 'CALLABLE_BOND', 'PUTABLE_BOND',
    'ABS', 'MBS', 'FX_FWD', 'FX_SWAP', 'IRS', 'CDS', 'OPTION', 'FUTURE'
}


@router.post("", response_model=InstrumentOut, status_code=201)
def create_instrument(req: InstrumentCreate):
    """Create a new instrument with initial version."""
    # Validate instrument type
    if req.instrument_type not in VALID_INSTRUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid instrument_type. Must be one of: {', '.join(sorted(VALID_INSTRUMENT_TYPES))}"
        )

    # Generate instrument ID
    instrument_id = f"{req.instrument_type.lower()}-{uuid4()}"

    try:
        with db_conn() as conn:
            # Insert into instrument table
            conn.execute(
                """
                INSERT INTO instrument (instrument_id, instrument_type, created_at)
                VALUES (%(iid)s, %(itype)s, now())
                """,
                {"iid": instrument_id, "itype": req.instrument_type}
            )

            # Create initial version
            conn.execute(
                """
                INSERT INTO instrument_version
                  (instrument_id, version, terms_json, status, created_at, updated_at)
                VALUES (%(iid)s, 1, %(terms)s::jsonb, 'APPROVED', now(), now())
                """,
                {"iid": instrument_id, "terms": req.terms_json}
            )

            # Fetch created instrument
            result = conn.execute(
                """
                SELECT i.instrument_id, i.instrument_type, iv.version, iv.terms_json,
                       iv.status, i.created_at
                FROM instrument i
                INNER JOIN instrument_version iv ON i.instrument_id = iv.instrument_id
                WHERE i.instrument_id = %(iid)s AND iv.version = 1
                """,
                {"iid": instrument_id}
            ).fetchone()

            return InstrumentOut(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("", response_model=List[InstrumentOut])
def list_instruments(
    instrument_type: Optional[str] = Query(None, description="Filter by instrument type"),
    search: Optional[str] = Query(None, description="Search instrument_id or issuer_id"),
    limit: int = Query(100, description="Max results", le=1000),
    offset: int = Query(0, description="Result offset", ge=0),
):
    """List instruments with filtering."""
    try:
        with db_conn() as conn:
            # Build dynamic WHERE clause
            where_parts = ["iv.status = 'APPROVED'"]
            params = {"lim": limit, "off": offset}

            if instrument_type:
                where_parts.append("i.instrument_type = %(itype)s")
                params["itype"] = instrument_type

            if search:
                where_parts.append(
                    "(i.instrument_id ILIKE %(search)s OR iv.terms_json ->> 'issuer_id' ILIKE %(search)s)"
                )
                params["search"] = f"%{search}%"

            where_clause = " AND ".join(where_parts)

            query = f"""
                SELECT i.instrument_id, i.instrument_type, iv.version, iv.terms_json,
                       iv.status, i.created_at
                FROM instrument i
                INNER JOIN instrument_version iv ON i.instrument_id = iv.instrument_id
                WHERE {where_clause}
                ORDER BY i.created_at DESC
                LIMIT %(lim)s OFFSET %(off)s
            """

            rows = conn.execute(query, params).fetchall()
            return [InstrumentOut(**row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{instrument_id}", response_model=InstrumentOut)
def get_instrument(instrument_id: str):
    """Get a single instrument by ID."""
    try:
        with db_conn() as conn:
            result = conn.execute(
                """
                SELECT i.instrument_id, i.instrument_type, iv.version, iv.terms_json,
                       iv.status, i.created_at
                FROM instrument i
                INNER JOIN instrument_version iv ON i.instrument_id = iv.instrument_id
                WHERE i.instrument_id = %(iid)s AND iv.status = 'APPROVED'
                ORDER BY iv.version DESC
                LIMIT 1
                """,
                {"iid": instrument_id}
            ).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail=f"Instrument not found: {instrument_id}")

            return InstrumentOut(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.patch("/{instrument_id}", response_model=InstrumentOut)
def update_instrument(instrument_id: str, req: InstrumentUpdate):
    """Update instrument by creating a new version."""
    try:
        with db_conn() as conn:
            # Check if instrument exists
            check = conn.execute(
                "SELECT 1 FROM instrument WHERE instrument_id = %(iid)s",
                {"iid": instrument_id}
            ).fetchone()

            if not check:
                raise HTTPException(status_code=404, detail=f"Instrument not found: {instrument_id}")

            # Create new version
            conn.execute(
                """
                INSERT INTO instrument_version
                  (instrument_id, version, terms_json, status, created_at, updated_at)
                SELECT instrument_id, MAX(version) + 1,
                       %(new_terms)s::jsonb, 'APPROVED', now(), now()
                FROM instrument_version
                WHERE instrument_id = %(iid)s
                GROUP BY instrument_id
                """,
                {"iid": instrument_id, "new_terms": req.terms_json}
            )

            # Fetch updated instrument
            result = conn.execute(
                """
                SELECT i.instrument_id, i.instrument_type, iv.version, iv.terms_json,
                       iv.status, i.created_at
                FROM instrument i
                INNER JOIN instrument_version iv ON i.instrument_id = iv.instrument_id
                WHERE i.instrument_id = %(iid)s
                ORDER BY iv.version DESC
                LIMIT 1
                """,
                {"iid": instrument_id}
            ).fetchone()

            return InstrumentOut(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{instrument_id}", status_code=204)
def delete_instrument(instrument_id: str):
    """Retire an instrument (soft delete)."""
    try:
        with db_conn() as conn:
            # Check for active positions
            position_count = conn.execute(
                "SELECT count(*) as cnt FROM position WHERE instrument_id = %(iid)s AND status='ACTIVE'",
                {"iid": instrument_id}
            ).fetchone()

            if position_count and position_count['cnt'] > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete instrument with active positions. Retire instead."
                )

            # Mark all versions as RETIRED
            conn.execute(
                "UPDATE instrument_version SET status='RETIRED' WHERE instrument_id = %(iid)s",
                {"iid": instrument_id}
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/bulk-create", response_model=BulkCreateResult)
def bulk_create_instruments(req: BulkInstrumentCreate):
    """Bulk create instruments in a transaction."""
    errors = []
    created_count = 0

    try:
        with db_conn() as conn:
            for idx, instr in enumerate(req.instruments):
                try:
                    # Validate type
                    if instr.instrument_type not in VALID_INSTRUMENT_TYPES:
                        errors.append({
                            "index": idx,
                            "error": f"Invalid instrument_type: {instr.instrument_type}"
                        })
                        continue

                    # Generate ID
                    instrument_id = f"{instr.instrument_type.lower()}-{uuid4()}"

                    # Insert instrument
                    conn.execute(
                        "INSERT INTO instrument (instrument_id, instrument_type, created_at) VALUES (%(iid)s, %(itype)s, now())",
                        {"iid": instrument_id, "itype": instr.instrument_type}
                    )

                    # Insert version
                    conn.execute(
                        """
                        INSERT INTO instrument_version
                          (instrument_id, version, terms_json, status, created_at, updated_at)
                        VALUES (%(iid)s, 1, %(terms)s::jsonb, 'APPROVED', now(), now())
                        """,
                        {"iid": instrument_id, "terms": instr.terms_json}
                    )

                    created_count += 1

                except Exception as e:
                    errors.append({"index": idx, "error": str(e)})

            # If any errors, rollback
            if errors:
                raise Exception("Bulk creation had errors")

    except Exception as e:
        # Transaction will auto-rollback on exception
        pass

    return BulkCreateResult(created_count=created_count, errors=errors)


@router.get("/{instrument_id}/versions", response_model=List[InstrumentVersionOut])
def get_instrument_versions(instrument_id: str):
    """Get version history for an instrument."""
    try:
        with db_conn() as conn:
            rows = conn.execute(
                """
                SELECT instrument_id, version, terms_json, status, created_at, updated_at
                FROM instrument_version
                WHERE instrument_id = %(iid)s
                ORDER BY version DESC
                """,
                {"iid": instrument_id}
            ).fetchall()

            if not rows:
                raise HTTPException(status_code=404, detail=f"Instrument not found: {instrument_id}")

            return [InstrumentVersionOut(**row) for row in rows]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
