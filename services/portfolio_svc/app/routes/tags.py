"""Segmentation and tagging endpoints."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.common.db import db_conn

router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class TagUpdate(BaseModel):
    """Request body for adding/removing tags."""
    tags: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/portfolio/{portfolio_id}", status_code=200)
def add_portfolio_tags(portfolio_id: str, req: TagUpdate):
    """Add tags to a portfolio node."""
    try:
        with db_conn() as conn:
            # Check portfolio exists
            portfolio = conn.execute(
                "SELECT tags_json FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id}
            ).fetchone()

            if not portfolio:
                raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

            # Merge new tags with existing
            existing_tags = portfolio['tags_json'] or {}
            for tag in req.tags:
                existing_tags[tag] = True

            # Update portfolio
            conn.execute(
                "UPDATE portfolio_node SET tags_json = %(tags)s::jsonb WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id, "tags": existing_tags}
            )

            # Fetch updated portfolio
            result = conn.execute(
                "SELECT portfolio_node_id, name, tags_json FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id}
            ).fetchone()

            return {
                "portfolio_id": result['portfolio_node_id'],
                "name": result['name'],
                "tags": list((result['tags_json'] or {}).keys())
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/portfolio/{portfolio_id}", status_code=200)
def remove_portfolio_tags(portfolio_id: str, req: TagUpdate):
    """Remove tags from a portfolio node."""
    try:
        with db_conn() as conn:
            # Check portfolio exists
            portfolio = conn.execute(
                "SELECT tags_json FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id}
            ).fetchone()

            if not portfolio:
                raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

            # Remove specified tags
            existing_tags = portfolio['tags_json'] or {}
            for tag in req.tags:
                existing_tags.pop(tag, None)

            # Update portfolio
            conn.execute(
                "UPDATE portfolio_node SET tags_json = %(tags)s::jsonb WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id, "tags": existing_tags}
            )

            # Fetch updated portfolio
            result = conn.execute(
                "SELECT portfolio_node_id, name, tags_json FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id}
            ).fetchone()

            return {
                "portfolio_id": result['portfolio_node_id'],
                "name": result['name'],
                "tags": list((result['tags_json'] or {}).keys())
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/portfolio", status_code=200)
def get_portfolios_by_tag(tag: str = Query(..., description="Tag to filter by")):
    """List all portfolios with a specific tag."""
    try:
        with db_conn() as conn:
            rows = conn.execute(
                """
                SELECT portfolio_node_id, name, node_type, tags_json
                FROM portfolio_node
                WHERE tags_json ? %(tag)s
                ORDER BY created_at DESC
                """,
                {"tag": tag}
            ).fetchall()

            portfolios = []
            for row in rows:
                portfolios.append({
                    "portfolio_id": row['portfolio_node_id'],
                    "name": row['name'],
                    "portfolio_type": row['node_type'],
                    "tags": list((row['tags_json'] or {}).keys())
                })

            return portfolios

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/position/{position_id}", status_code=200)
def add_position_tags(position_id: str, req: TagUpdate):
    """Add tags to a position."""
    try:
        with db_conn() as conn:
            # Check position exists
            position = conn.execute(
                "SELECT tags_json FROM position WHERE position_id = %(pid)s",
                {"pid": position_id}
            ).fetchone()

            if not position:
                raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")

            # Merge new tags with existing
            existing_tags = position['tags_json'] or {}
            for tag in req.tags:
                existing_tags[tag] = True

            # Update position
            conn.execute(
                "UPDATE position SET tags_json = %(tags)s::jsonb, updated_at = now() WHERE position_id = %(pid)s",
                {"pid": position_id, "tags": existing_tags}
            )

            # Fetch updated position
            result = conn.execute(
                "SELECT position_id, tags_json FROM position WHERE position_id = %(pid)s",
                {"pid": position_id}
            ).fetchone()

            return {
                "position_id": result['position_id'],
                "tags": list((result['tags_json'] or {}).keys())
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/position/{position_id}", status_code=200)
def remove_position_tags(position_id: str, req: TagUpdate):
    """Remove tags from a position."""
    try:
        with db_conn() as conn:
            # Check position exists
            position = conn.execute(
                "SELECT tags_json FROM position WHERE position_id = %(pid)s",
                {"pid": position_id}
            ).fetchone()

            if not position:
                raise HTTPException(status_code=404, detail=f"Position not found: {position_id}")

            # Remove specified tags
            existing_tags = position['tags_json'] or {}
            for tag in req.tags:
                existing_tags.pop(tag, None)

            # Update position
            conn.execute(
                "UPDATE position SET tags_json = %(tags)s::jsonb, updated_at = now() WHERE position_id = %(pid)s",
                {"pid": position_id, "tags": existing_tags}
            )

            # Fetch updated position
            result = conn.execute(
                "SELECT position_id, tags_json FROM position WHERE position_id = %(pid)s",
                {"pid": position_id}
            ).fetchone()

            return {
                "position_id": result['position_id'],
                "tags": list((result['tags_json'] or {}).keys())
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/position", status_code=200)
def get_positions_by_tag(tag: str = Query(..., description="Tag to filter by")):
    """List all positions with a specific tag."""
    try:
        with db_conn() as conn:
            rows = conn.execute(
                """
                SELECT position_id, portfolio_node_id, instrument_id, tags_json
                FROM position
                WHERE tags_json ? %(tag)s AND status = 'ACTIVE'
                ORDER BY created_at DESC
                """,
                {"tag": tag}
            ).fetchall()

            positions = []
            for row in rows:
                positions.append({
                    "position_id": row['position_id'],
                    "portfolio_id": row['portfolio_node_id'],
                    "instrument_id": row['instrument_id'],
                    "tags": list((row['tags_json'] or {}).keys())
                })

            return positions

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/all", status_code=200)
def list_all_tags():
    """List all unique tags across portfolios and positions."""
    try:
        with db_conn() as conn:
            # Get tags from portfolios
            portfolio_tags = conn.execute(
                """
                SELECT DISTINCT jsonb_object_keys(tags_json) AS tag
                FROM portfolio_node
                WHERE tags_json IS NOT NULL AND tags_json != '{}'::jsonb
                """
            ).fetchall()

            # Get tags from positions
            position_tags = conn.execute(
                """
                SELECT DISTINCT jsonb_object_keys(tags_json) AS tag
                FROM position
                WHERE tags_json IS NOT NULL AND tags_json != '{}'::jsonb
                  AND status = 'ACTIVE'
                """
            ).fetchall()

            # Combine and deduplicate
            all_tags = set()
            for row in portfolio_tags:
                all_tags.add(row['tag'])
            for row in position_tags:
                all_tags.add(row['tag'])

            return {"tags": sorted(list(all_tags))}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
