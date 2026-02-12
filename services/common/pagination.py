"""Cursor-based and offset pagination helpers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Standard pagination query parameters."""
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=1000)


class PaginatedResponse(BaseModel):
    """Standard paginated response wrapper."""
    data: List[Any]
    offset: int
    limit: int
    total: int
    has_more: bool


def paginate(items: List[Any], offset: int, limit: int, total: Optional[int] = None) -> PaginatedResponse:
    """Build a paginated response from a list of items.

    If total is not provided, len(items) is used (suitable for in-memory pagination).
    For DB pagination, pass the COUNT(*) result as total.
    """
    actual_total = total if total is not None else len(items)
    return PaginatedResponse(
        data=items,
        offset=offset,
        limit=limit,
        total=actual_total,
        has_more=(offset + limit) < actual_total,
    )


def pagination_sql(offset: int, limit: int) -> str:
    """Generate OFFSET/LIMIT SQL clause."""
    return f"OFFSET {offset} LIMIT {limit}"
