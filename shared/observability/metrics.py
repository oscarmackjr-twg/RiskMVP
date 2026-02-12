"""CloudWatch metrics helpers.

Stub implementation - wire to boto3 CloudWatch client in production.
"""
from __future__ import annotations

from typing import Dict, Optional


def put_metric(
    namespace: str,
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: Optional[Dict[str, str]] = None,
) -> None:
    """Publish a metric to CloudWatch.

    Stub: logs to stdout in development.
    """
    raise NotImplementedError("Wire to boto3 CloudWatch put_metric_data")


def increment_counter(namespace: str, metric_name: str, dimensions: Optional[Dict[str, str]] = None) -> None:
    """Increment a counter metric by 1."""
    raise NotImplementedError("Wire to boto3 CloudWatch put_metric_data")
