"""Base event model for all domain events."""
from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from uuid import uuid4


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_service: str = ""
    correlation_id: str = ""
    payload: dict = Field(default_factory=dict)
