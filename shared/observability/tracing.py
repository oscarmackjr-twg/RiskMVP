"""AWS X-Ray tracing setup.

Stub implementation - wire to aws-xray-sdk in production.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator


@contextmanager
def trace_segment(name: str) -> Generator[None, None, None]:
    """Create an X-Ray trace segment.

    Stub: no-op in development.
    """
    yield


@contextmanager
def trace_subsegment(name: str) -> Generator[None, None, None]:
    """Create an X-Ray trace subsegment.

    Stub: no-op in development.
    """
    yield
