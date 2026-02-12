"""Events related to market data lifecycle."""
from __future__ import annotations

from shared.events.base import BaseEvent


class SnapshotIngested(BaseEvent):
    event_type: str = "marketdata.snapshot_ingested"
    source_service: str = "marketdata_svc"


class CurvePublished(BaseEvent):
    event_type: str = "marketdata.curve_published"
    source_service: str = "marketdata_svc"
