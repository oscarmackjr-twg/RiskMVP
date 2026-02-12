"""Events related to run lifecycle."""
from __future__ import annotations

from shared.events.base import BaseEvent


class RunCreated(BaseEvent):
    event_type: str = "run.created"
    source_service: str = "run_orchestrator"


class RunCompleted(BaseEvent):
    event_type: str = "run.completed"
    source_service: str = "run_orchestrator"


class TaskFailed(BaseEvent):
    event_type: str = "task.failed"
    source_service: str = "compute_worker"
