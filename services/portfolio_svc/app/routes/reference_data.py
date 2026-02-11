"""Reference data endpoints - CRUD for issuers, sectors, ratings."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.common.db import db_conn

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class ReferenceDataCreate(BaseModel):
    """Create a reference data entity."""
    entity_type: Literal["ISSUER", "SECTOR", "GEOGRAPHY", "CURRENCY"]
    name: str
    ticker: Optional[str] = None
    cusip: Optional[str] = None
    isin: Optional[str] = None
    sector: Optional[str] = None
    geography: Optional[str] = None
    currency: Optional[str] = None
    parent_entity_id: Optional[str] = None
    metadata_json: Optional[Dict] = Field(default_factory=dict)


class ReferenceDataUpdate(BaseModel):
    """Update reference data entity (all fields optional)."""
    name: Optional[str] = None
    ticker: Optional[str] = None
    cusip: Optional[str] = None
    isin: Optional[str] = None
    sector: Optional[str] = None
    geography: Optional[str] = None
    currency: Optional[str] = None
    parent_entity_id: Optional[str] = None
    metadata_json: Optional[Dict] = None


class ReferenceDataOut(BaseModel):
    """Reference data entity response."""
    entity_id: str
    entity_type: str
    name: str
    ticker: Optional[str] = None
    cusip: Optional[str] = None
    isin: Optional[str] = None
    sector: Optional[str] = None
    geography: Optional[str] = None
    currency: Optional[str] = None
    parent_entity_id: Optional[str] = None
    metadata_json: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RatingHistoryCreate(BaseModel):
    """Add a rating history entry."""
    agency: Literal["SP", "MOODYS", "FITCH", "DBRS"]
    rating: str
    outlook: Optional[str] = None
    as_of_date: datetime
    effective_date: Optional[datetime] = None
    metadata_json: Optional[Dict] = Field(default_factory=dict)


class RatingHistoryOut(BaseModel):
    """Rating history entry response."""
    rating_id: str
    entity_id: str
    agency: str
    rating: str
    outlook: Optional[str] = None
    as_of_date: datetime
    effective_date: Optional[datetime] = None
    metadata_json: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=ReferenceDataOut, status_code=201)
def create_reference_data(req: ReferenceDataCreate):
    """Create a reference data entity (issuer, sector, geography, currency)."""
    entity_id = f"{req.entity_type.lower()}-{uuid4()}"

    with db_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO reference_data (
                    entity_id, entity_type, name, ticker, cusip, isin,
                    sector, geography, currency, parent_entity_id, metadata_json
                ) VALUES (
                    %(entity_id)s, %(entity_type)s, %(name)s, %(ticker)s, %(cusip)s, %(isin)s,
                    %(sector)s, %(geography)s, %(currency)s, %(parent_entity_id)s, %(metadata_json)s
                )
                """,
                {
                    "entity_id": entity_id,
                    "entity_type": req.entity_type,
                    "name": req.name,
                    "ticker": req.ticker,
                    "cusip": req.cusip,
                    "isin": req.isin,
                    "sector": req.sector,
                    "geography": req.geography,
                    "currency": req.currency,
                    "parent_entity_id": req.parent_entity_id,
                    "metadata_json": req.metadata_json,
                }
            )

            row = conn.execute(
                "SELECT * FROM reference_data WHERE entity_id = %(entity_id)s",
                {"entity_id": entity_id}
            ).fetchone()

            return ReferenceDataOut(**row)
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail="Duplicate ticker or cusip")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[ReferenceDataOut])
def list_reference_data(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    geography: Optional[str] = Query(None, description="Filter by geography"),
    search: Optional[str] = Query(None, description="Search name/ticker/cusip"),
):
    """List reference data with optional filtering."""
    conditions = []
    params = {}

    if entity_type:
        conditions.append("entity_type = %(entity_type)s")
        params["entity_type"] = entity_type

    if sector:
        conditions.append("sector = %(sector)s")
        params["sector"] = sector

    if geography:
        conditions.append("geography = %(geography)s")
        params["geography"] = geography

    if search:
        conditions.append("(name ILIKE %(search)s OR ticker ILIKE %(search)s OR cusip ILIKE %(search)s)")
        params["search"] = f"%{search}%"

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with db_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM reference_data
            {where_clause}
            ORDER BY created_at DESC
            """,
            params
        ).fetchall()

        return [ReferenceDataOut(**row) for row in rows]


@router.get("/{entity_id}", response_model=ReferenceDataOut)
def get_reference_data(entity_id: str):
    """Get a single reference data entity."""
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM reference_data WHERE entity_id = %(entity_id)s",
            {"entity_id": entity_id}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Reference data not found")

        return ReferenceDataOut(**row)


@router.patch("/{entity_id}", response_model=ReferenceDataOut)
def update_reference_data(entity_id: str, req: ReferenceDataUpdate):
    """Update a reference data entity."""
    updates = []
    params = {"entity_id": entity_id}

    for field, value in req.dict(exclude_unset=True).items():
        if value is not None:
            updates.append(f"{field} = %({field})s")
            params[field] = value

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = now()")

    with db_conn() as conn:
        result = conn.execute(
            f"""
            UPDATE reference_data
            SET {', '.join(updates)}
            WHERE entity_id = %(entity_id)s
            """,
            params
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Reference data not found")

        row = conn.execute(
            "SELECT * FROM reference_data WHERE entity_id = %(entity_id)s",
            {"entity_id": entity_id}
        ).fetchone()

        return ReferenceDataOut(**row)


@router.post("/{entity_id}/rating", response_model=RatingHistoryOut, status_code=201)
def add_rating(entity_id: str, req: RatingHistoryCreate):
    """Add a rating history entry to an entity."""
    rating_id = f"rating-{uuid4()}"

    with db_conn() as conn:
        # Verify entity exists
        entity = conn.execute(
            "SELECT entity_id FROM reference_data WHERE entity_id = %(entity_id)s",
            {"entity_id": entity_id}
        ).fetchone()

        if not entity:
            raise HTTPException(status_code=404, detail="Reference data entity not found")

        conn.execute(
            """
            INSERT INTO rating_history (
                rating_id, entity_id, agency, rating, outlook,
                as_of_date, effective_date, metadata_json
            ) VALUES (
                %(rating_id)s, %(entity_id)s, %(agency)s, %(rating)s, %(outlook)s,
                %(as_of_date)s, %(effective_date)s, %(metadata_json)s
            )
            """,
            {
                "rating_id": rating_id,
                "entity_id": entity_id,
                "agency": req.agency,
                "rating": req.rating,
                "outlook": req.outlook,
                "as_of_date": req.as_of_date,
                "effective_date": req.effective_date,
                "metadata_json": req.metadata_json,
            }
        )

        row = conn.execute(
            "SELECT * FROM rating_history WHERE rating_id = %(rating_id)s",
            {"rating_id": rating_id}
        ).fetchone()

        return RatingHistoryOut(**row)


@router.get("/{entity_id}/ratings", response_model=List[RatingHistoryOut])
def get_rating_history(entity_id: str):
    """Get rating history for an entity (all agencies, sorted by date)."""
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM rating_history
            WHERE entity_id = %(entity_id)s
            ORDER BY as_of_date DESC
            """,
            {"entity_id": entity_id}
        ).fetchall()

        return [RatingHistoryOut(**row) for row in rows]


@router.get("/{entity_id}/current-rating", response_model=Dict[str, RatingHistoryOut])
def get_current_ratings(entity_id: str):
    """Get latest rating per agency for an entity."""
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT ON (agency) *
            FROM rating_history
            WHERE entity_id = %(entity_id)s
            ORDER BY agency, as_of_date DESC
            """,
            {"entity_id": entity_id}
        ).fetchall()

        return {row["agency"]: RatingHistoryOut(**row) for row in rows}
