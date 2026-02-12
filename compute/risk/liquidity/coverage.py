"""Liquidity Coverage Ratio (LCR) calculation."""
from __future__ import annotations


def liquidity_coverage_ratio(hqla: float, net_outflows_30d: float) -> float:
    """Calculate LCR = HQLA / Net Cash Outflows (30 day).

    Regulatory minimum is typically 100%.
    """
    if net_outflows_30d == 0:
        return float("inf")
    return hqla / net_outflows_30d
