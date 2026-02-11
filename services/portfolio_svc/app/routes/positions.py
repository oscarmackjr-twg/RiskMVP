"""Position tracking and holdings endpoints."""
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from services.portfolio_svc.app.models import (
    PositionCreate,
    PositionOut,
    PositionUpdate,
)
from services.common.db import db_conn

router = APIRouter()


@router.get("", response_model=List[PositionOut])
def list_positions(
    portfolio_id: Optional[str] = Query(None, description="Filter by portfolio"),
    instrument_id: Optional[str] = Query(None, description="Filter by instrument"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, description="Max results", le=1000),
    offset: int = Query(0, description="Result offset", ge=0),
):
    """List positions with optional filters."""
    try:
        with db_conn() as conn:
            # Build dynamic WHERE clause
            where_parts = []
            params = {"lim": limit, "off": offset}

            if portfolio_id:
                where_parts.append("portfolio_node_id = %(port_id)s")
                params["port_id"] = portfolio_id

            if instrument_id:
                where_parts.append("instrument_id = %(inst_id)s")
                params["inst_id"] = instrument_id

            if status:
                where_parts.append("status = %(status)s")
                params["status"] = status
            else:
                # Default to ACTIVE only
                where_parts.append("status = 'ACTIVE'")

            where_clause = " AND ".join(where_parts) if where_parts else "1=1"

            query = f"""
                SELECT position_id, portfolio_node_id, instrument_id, quantity,
                       base_ccy, cost_basis, book_value, tags_json, status,
                       created_at, updated_at
                FROM position
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %(lim)s OFFSET %(off)s
            """

            rows = conn.execute(query, params).fetchall()

            positions = []
            for row in rows:
                positions.append(PositionOut(
                    position_id=row['position_id'],
                    portfolio_id=row['portfolio_node_id'],
                    instrument_id=row['instrument_id'],
                    product_type='UNKNOWN',  # Would need to join to instrument table
                    quantity=float(row['quantity']),
                    cost_basis=float(row['cost_basis']) if row['cost_basis'] else None,
                    currency=row['base_ccy'],
                    metadata=row['tags_json'] or {},
                    created_at=row['created_at']
                ))

            return positions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("", response_model=PositionOut, status_code=201)
def create_position(req: PositionCreate):
    """Add a new position to a portfolio."""
    try:
        with db_conn() as conn:
            # Validate portfolio exists
            portfolio = conn.execute(
                "SELECT 1 FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                {"pid": req.portfolio_id}
            ).fetchone()

            if not portfolio:
                raise HTTPException(
                    status_code=404,
                    detail=f"Portfolio not found: {req.portfolio_id}"
                )

            # Validate instrument exists
            instrument = conn.execute(
                "SELECT 1 FROM instrument WHERE instrument_id = %(iid)s",
                {"iid": req.instrument_id}
            ).fetchone()

            if not instrument:
                raise HTTPException(
                    status_code=404,
                    detail=f"Instrument not found: {req.instrument_id}"
                )

            # Generate position ID
            position_id = req.position_id if hasattr(req, 'position_id') and req.position_id else f"pos-{uuid4()}"

            # Insert position
            conn.execute(
                """
                INSERT INTO position
                  (position_id, portfolio_node_id, instrument_id, quantity, base_ccy,
                   cost_basis, book_value, tags_json, status, created_at, updated_at)
                VALUES (%(pid)s, %(port_id)s, %(inst_id)s, %(qty)s, %(ccy)s,
                        %(cost)s, %(book)s, %(tags)s::jsonb, 'ACTIVE', now(), now())
                """,
                {
                    "pid": position_id,
                    "port_id": req.portfolio_id,
                    "inst_id": req.instrument_id,
                    "qty": req.quantity,
                    "ccy": req.currency,
                    "cost": req.cost_basis,
                    "book": req.cost_basis,  # Default book_value to cost_basis
                    "tags": req.metadata or {}
                }
            )

            # Fetch created position
            result = conn.execute(
                """
                SELECT position_id, portfolio_node_id, instrument_id, quantity,
                       base_ccy, cost_basis, book_value, tags_json, status, created_at
                FROM position
                WHERE position_id = %(pid)s
                """,
                {"pid": position_id}
            ).fetchone()

            return PositionOut(
                position_id=result['position_id'],
                portfolio_id=result['portfolio_node_id'],
                instrument_id=result['instrument_id'],
                product_type=req.product_type,
                quantity=float(result['quantity']),
                cost_basis=float(result['cost_basis']) if result['cost_basis'] else None,
                currency=result['base_ccy'],
                metadata=result['tags_json'] or {},
                created_at=result['created_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{position_id}", response_model=PositionOut)
def get_position(position_id: str):
    """Get a single position by ID."""
    try:
        with db_conn() as conn:
            result = conn.execute(
                """
                SELECT p.position_id, p.portfolio_node_id, p.instrument_id, p.quantity,
                       p.base_ccy, p.cost_basis, p.book_value, p.tags_json, p.status,
                       p.created_at, i.instrument_type
                FROM position p
                LEFT JOIN instrument i ON p.instrument_id = i.instrument_id
                WHERE p.position_id = %(pid)s
                """,
                {"pid": position_id}
            ).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")

            return PositionOut(
                position_id=result['position_id'],
                portfolio_id=result['portfolio_node_id'],
                instrument_id=result['instrument_id'],
                product_type=result['instrument_type'] or 'UNKNOWN',
                quantity=float(result['quantity']),
                cost_basis=float(result['cost_basis']) if result['cost_basis'] else None,
                currency=result['base_ccy'],
                metadata=result['tags_json'] or {},
                created_at=result['created_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.patch("/{position_id}", response_model=PositionOut)
def update_position(position_id: str, req: PositionUpdate):
    """Partially update a position (e.g. adjust quantity)."""
    try:
        with db_conn() as conn:
            # Build dynamic update
            updates = []
            params = {"pid": position_id}

            if req.quantity is not None:
                updates.append("quantity = %(qty)s")
                params["qty"] = req.quantity

            if req.cost_basis is not None:
                updates.append("cost_basis = %(cost)s")
                params["cost"] = req.cost_basis

            if req.metadata is not None:
                updates.append("tags_json = %(tags)s::jsonb")
                params["tags"] = req.metadata

            if not updates:
                # Nothing to update, just return current
                return get_position(position_id)

            # Add updated_at
            updates.append("updated_at = now()")

            # Execute update
            conn.execute(
                f"UPDATE position SET {', '.join(updates)} WHERE position_id = %(pid)s",
                params
            )

            return get_position(position_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{position_id}", status_code=204)
def delete_position(position_id: str):
    """Remove a position from the portfolio (soft delete)."""
    try:
        with db_conn() as conn:
            # Soft delete - set status to DELETED
            conn.execute(
                "UPDATE position SET status = 'DELETED', updated_at = now() WHERE position_id = %(pid)s",
                {"pid": position_id}
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/portfolio/{portfolio_id}/holdings", response_model=List[PositionOut])
def get_portfolio_holdings(
    portfolio_id: str,
    include_children: bool = Query(False, description="Include positions from child portfolios"),
):
    """Get all holdings for a portfolio, optionally including child portfolios."""
    try:
        with db_conn() as conn:
            if include_children:
                # Use recursive query to get all descendants
                query = """
                    WITH RECURSIVE descendants AS (
                      SELECT portfolio_node_id FROM portfolio_node WHERE portfolio_node_id = %(pid)s
                      UNION ALL
                      SELECT pn.portfolio_node_id
                      FROM portfolio_node pn
                      INNER JOIN descendants d ON pn.parent_id = d.portfolio_node_id
                    )
                    SELECT p.position_id, p.portfolio_node_id, p.instrument_id, p.quantity,
                           p.base_ccy, p.cost_basis, p.book_value, p.tags_json, p.status,
                           p.created_at, i.instrument_type
                    FROM position p
                    LEFT JOIN instrument i ON p.instrument_id = i.instrument_id
                    INNER JOIN descendants d ON p.portfolio_node_id = d.portfolio_node_id
                    WHERE p.status = 'ACTIVE'
                    ORDER BY p.created_at DESC
                """
            else:
                # Just direct positions
                query = """
                    SELECT p.position_id, p.portfolio_node_id, p.instrument_id, p.quantity,
                           p.base_ccy, p.cost_basis, p.book_value, p.tags_json, p.status,
                           p.created_at, i.instrument_type
                    FROM position p
                    LEFT JOIN instrument i ON p.instrument_id = i.instrument_id
                    WHERE p.portfolio_node_id = %(pid)s AND p.status = 'ACTIVE'
                    ORDER BY p.created_at DESC
                """

            rows = conn.execute(query, {"pid": portfolio_id}).fetchall()

            positions = []
            for row in rows:
                positions.append(PositionOut(
                    position_id=row['position_id'],
                    portfolio_id=row['portfolio_node_id'],
                    instrument_id=row['instrument_id'],
                    product_type=row['instrument_type'] or 'UNKNOWN',
                    quantity=float(row['quantity']),
                    cost_basis=float(row['cost_basis']) if row['cost_basis'] else None,
                    currency=row['base_ccy'],
                    metadata=row['tags_json'] or {},
                    created_at=row['created_at']
                ))

            return positions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/portfolio/{portfolio_id}/summary")
def get_holdings_summary(portfolio_id: str):
    """Get summary statistics for portfolio holdings (count, total notional, etc.)."""
    try:
        with db_conn() as conn:
            result = conn.execute(
                """
                SELECT
                  COUNT(*) as position_count,
                  COUNT(DISTINCT instrument_id) as instrument_count,
                  SUM(quantity) as total_quantity,
                  SUM(cost_basis) as total_cost_basis,
                  SUM(book_value) as total_book_value
                FROM position
                WHERE portfolio_node_id = %(pid)s AND status = 'ACTIVE'
                """,
                {"pid": portfolio_id}
            ).fetchone()

            return {
                "portfolio_id": portfolio_id,
                "position_count": result['position_count'],
                "instrument_count": result['instrument_count'],
                "total_quantity": float(result['total_quantity']) if result['total_quantity'] else 0.0,
                "total_cost_basis": float(result['total_cost_basis']) if result['total_cost_basis'] else 0.0,
                "total_book_value": float(result['total_book_value']) if result['total_book_value'] else 0.0,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{position_id}/valuation")
def get_position_valuation(position_id: str):
    """Get latest valuation for position."""
    try:
        with db_conn() as conn:
            result = conn.execute(
                """
                SELECT vr.*, r.as_of_time
                FROM valuation_result vr
                INNER JOIN run r ON vr.run_id = r.run_id
                WHERE vr.position_id = %(pid)s
                  AND vr.scenario_id = 'BASE'
                ORDER BY r.as_of_time DESC
                LIMIT 1
                """,
                {"pid": position_id}
            ).fetchone()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"No valuation found for position: {position_id}"
                )

            return {
                "position_id": result['position_id'],
                "run_id": result['run_id'],
                "scenario_id": result['scenario_id'],
                "measures": result['measures_json'],
                "as_of_time": result['as_of_time']
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/by-portfolio/{portfolio_node_id}", response_model=List[PositionOut])
def list_positions_by_portfolio(portfolio_node_id: str):
    """List positions for portfolio with instrument details."""
    try:
        with db_conn() as conn:
            rows = conn.execute(
                """
                SELECT p.position_id, p.portfolio_node_id, p.instrument_id, p.quantity,
                       p.base_ccy, p.cost_basis, p.book_value, p.tags_json, p.status,
                       p.created_at, i.instrument_type
                FROM position p
                LEFT JOIN instrument i ON p.instrument_id = i.instrument_id
                WHERE p.portfolio_node_id = %(pid)s AND p.status = 'ACTIVE'
                ORDER BY p.created_at DESC
                """,
                {"pid": portfolio_node_id}
            ).fetchall()

            positions = []
            for row in rows:
                positions.append(PositionOut(
                    position_id=row['position_id'],
                    portfolio_id=row['portfolio_node_id'],
                    instrument_id=row['instrument_id'],
                    product_type=row['instrument_type'] or 'UNKNOWN',
                    quantity=float(row['quantity']),
                    cost_basis=float(row['cost_basis']) if row['cost_basis'] else None,
                    currency=row['base_ccy'],
                    metadata=row['tags_json'] or {},
                    created_at=row['created_at']
                ))

            return positions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
