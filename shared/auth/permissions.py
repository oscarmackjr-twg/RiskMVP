"""Portfolio-level entitlements and access control.

Stub implementation - replace with actual RBAC/ABAC in production.
"""
from __future__ import annotations

from enum import Enum
from typing import List


class Permission(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    APPROVE = "APPROVE"
    ADMIN = "ADMIN"


def check_portfolio_access(user_id: str, portfolio_node_id: str, permission: Permission) -> bool:
    """Check if user has the given permission on a portfolio node.

    Stub: returns True for all checks.
    """
    return True


def get_accessible_portfolios(user_id: str, permission: Permission) -> List[str]:
    """Return portfolio node IDs accessible by user with given permission.

    Stub: returns wildcard access.
    """
    return ["*"]
