"""Portfolio CRUD and hierarchy endpoints."""
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.portfolio_svc.app.models import (
    PortfolioCreate,
    PortfolioOut,
    PortfolioTreeNode,
    PortfolioUpdate,
)
from services.common.db import db_conn
from services.common.portfolio_queries import build_hierarchy_tree_query, build_tree_structure

router = APIRouter()


class ReparentRequest(BaseModel):
    """Request body for reparenting a portfolio."""
    new_parent_id: Optional[str] = None


@router.get("", response_model=List[PortfolioOut])
def list_portfolios():
    """List all root portfolios (no parent)."""
    try:
        with db_conn() as conn:
            rows = conn.execute(
                """
                SELECT portfolio_node_id, name, parent_id, node_type,
                       tags_json, metadata_json, created_at
                FROM portfolio_node
                WHERE parent_id IS NULL
                ORDER BY created_at DESC
                """
            ).fetchall()

            # Convert to PortfolioOut model format
            portfolios = []
            for row in rows:
                portfolios.append(PortfolioOut(
                    portfolio_id=row['portfolio_node_id'],
                    name=row['name'],
                    parent_id=row['parent_id'],
                    portfolio_type=row['node_type'],
                    currency='USD',  # Default for now
                    metadata=row['metadata_json'] or {},
                    created_at=row['created_at']
                ))

            return portfolios

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("", response_model=PortfolioOut, status_code=201)
def create_portfolio(req: PortfolioCreate):
    """Create a new portfolio node."""
    try:
        with db_conn() as conn:
            # Validate parent exists if provided
            if req.parent_id:
                parent = conn.execute(
                    "SELECT 1 FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                    {"pid": req.parent_id}
                ).fetchone()
                if not parent:
                    raise HTTPException(status_code=404, detail=f"Parent portfolio not found: {req.parent_id}")

            # Generate portfolio ID
            portfolio_id = req.portfolio_id if hasattr(req, 'portfolio_id') and req.portfolio_id else f"port-{uuid4()}"

            # Insert portfolio node
            conn.execute(
                """
                INSERT INTO portfolio_node
                  (portfolio_node_id, parent_id, name, node_type, tags_json, metadata_json, created_at)
                VALUES (%(pid)s, %(parent)s, %(name)s, %(ntype)s, %(tags)s::jsonb, %(meta)s::jsonb, now())
                """,
                {
                    "pid": portfolio_id,
                    "parent": req.parent_id,
                    "name": req.name,
                    "ntype": req.portfolio_type,
                    "tags": {},
                    "meta": req.metadata or {}
                }
            )

            # Fetch created portfolio
            result = conn.execute(
                """
                SELECT portfolio_node_id, name, parent_id, node_type, metadata_json, created_at
                FROM portfolio_node
                WHERE portfolio_node_id = %(pid)s
                """,
                {"pid": portfolio_id}
            ).fetchone()

            return PortfolioOut(
                portfolio_id=result['portfolio_node_id'],
                name=result['name'],
                parent_id=result['parent_id'],
                portfolio_type=result['node_type'],
                currency='USD',
                metadata=result['metadata_json'] or {},
                created_at=result['created_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{portfolio_id}", response_model=PortfolioOut)
def get_portfolio(portfolio_id: str):
    """Get a single portfolio by ID."""
    try:
        with db_conn() as conn:
            result = conn.execute(
                """
                SELECT portfolio_node_id, name, parent_id, node_type, metadata_json, created_at
                FROM portfolio_node
                WHERE portfolio_node_id = %(pid)s
                """,
                {"pid": portfolio_id}
            ).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

            return PortfolioOut(
                portfolio_id=result['portfolio_node_id'],
                name=result['name'],
                parent_id=result['parent_id'],
                portfolio_type=result['node_type'],
                currency='USD',
                metadata=result['metadata_json'] or {},
                created_at=result['created_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.patch("/{portfolio_id}", response_model=PortfolioOut)
def update_portfolio(portfolio_id: str, req: PortfolioUpdate):
    """Partially update a portfolio."""
    try:
        with db_conn() as conn:
            # Build dynamic update
            updates = []
            params = {"pid": portfolio_id}

            if req.name is not None:
                updates.append("name = %(name)s")
                params["name"] = req.name

            if req.metadata is not None:
                updates.append("metadata_json = %(meta)s::jsonb")
                params["meta"] = req.metadata

            if not updates:
                # Nothing to update, just return current
                return get_portfolio(portfolio_id)

            # Execute update
            conn.execute(
                f"UPDATE portfolio_node SET {', '.join(updates)} WHERE portfolio_node_id = %(pid)s",
                params
            )

            return get_portfolio(portfolio_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: str):
    """Delete a portfolio node."""
    try:
        with db_conn() as conn:
            # Check for children
            children = conn.execute(
                "SELECT count(*) as cnt FROM portfolio_node WHERE parent_id = %(pid)s",
                {"pid": portfolio_id}
            ).fetchone()

            if children and children['cnt'] > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete portfolio with children"
                )

            # Check for positions
            positions = conn.execute(
                "SELECT count(*) as cnt FROM position WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id}
            ).fetchone()

            if positions and positions['cnt'] > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete portfolio with positions"
                )

            # Delete portfolio
            conn.execute(
                "DELETE FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id}
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{portfolio_id}/tree", response_model=PortfolioTreeNode)
def get_portfolio_tree(
    portfolio_id: str,
    run_id: Optional[str] = Query(None, description="Run ID for PV aggregation")
):
    """Get the full hierarchy tree rooted at the given portfolio."""
    try:
        with db_conn() as conn:
            # Build and execute hierarchy query
            query, params = build_hierarchy_tree_query(portfolio_id, run_id)
            rows = conn.execute(query, params).fetchall()

            if not rows:
                raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

            # Convert flat rows to tree structure
            tree = build_tree_structure(rows)

            if not tree:
                raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

            # Convert to PortfolioTreeNode (simplified - just ID, name, type, children)
            def convert_to_tree_node(node):
                return PortfolioTreeNode(
                    portfolio_id=node['portfolio_node_id'],
                    name=node['name'],
                    portfolio_type=node['node_type'],
                    children=[convert_to_tree_node(child) for child in node.get('children', [])]
                )

            return convert_to_tree_node(tree)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{portfolio_id}/children", response_model=List[PortfolioOut])
def get_portfolio_children(portfolio_id: str):
    """Get direct children of a portfolio node."""
    try:
        with db_conn() as conn:
            # Check parent exists
            parent = conn.execute(
                "SELECT 1 FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id}
            ).fetchone()

            if not parent:
                raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

            # Get children
            rows = conn.execute(
                """
                SELECT portfolio_node_id, name, parent_id, node_type, metadata_json, created_at
                FROM portfolio_node
                WHERE parent_id = %(pid)s
                ORDER BY created_at ASC
                """,
                {"pid": portfolio_id}
            ).fetchall()

            portfolios = []
            for row in rows:
                portfolios.append(PortfolioOut(
                    portfolio_id=row['portfolio_node_id'],
                    name=row['name'],
                    parent_id=row['parent_id'],
                    portfolio_type=row['node_type'],
                    currency='USD',
                    metadata=row['metadata_json'] or {},
                    created_at=row['created_at']
                ))

            return portfolios

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/{portfolio_id}/reparent", response_model=PortfolioOut)
def reparent_portfolio(portfolio_id: str, req: ReparentRequest):
    """Move a portfolio under a different parent node."""
    try:
        with db_conn() as conn:
            # Validate portfolio exists
            portfolio = conn.execute(
                "SELECT 1 FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id}
            ).fetchone()

            if not portfolio:
                raise HTTPException(status_code=404, detail=f"Portfolio not found: {portfolio_id}")

            # Validate new parent exists (if provided)
            if req.new_parent_id:
                new_parent = conn.execute(
                    "SELECT 1 FROM portfolio_node WHERE portfolio_node_id = %(pid)s",
                    {"pid": req.new_parent_id}
                ).fetchone()

                if not new_parent:
                    raise HTTPException(status_code=404, detail=f"New parent portfolio not found: {req.new_parent_id}")

                # Check if new parent is a descendant (would create cycle)
                # Use recursive query to find all descendants
                descendants = conn.execute(
                    """
                    WITH RECURSIVE descendants AS (
                      SELECT portfolio_node_id FROM portfolio_node WHERE portfolio_node_id = %(pid)s
                      UNION ALL
                      SELECT pn.portfolio_node_id
                      FROM portfolio_node pn
                      INNER JOIN descendants d ON pn.parent_id = d.portfolio_node_id
                    )
                    SELECT 1 FROM descendants WHERE portfolio_node_id = %(new_pid)s
                    """,
                    {"pid": portfolio_id, "new_pid": req.new_parent_id}
                ).fetchone()

                if descendants:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot reparent: new parent is a descendant (would create cycle)"
                    )

            # Update parent
            conn.execute(
                "UPDATE portfolio_node SET parent_id = %(new_pid)s WHERE portfolio_node_id = %(pid)s",
                {"pid": portfolio_id, "new_pid": req.new_parent_id}
            )

            return get_portfolio(portfolio_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
