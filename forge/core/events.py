"""Event types for the ForgeLab pipeline lifecycle.

Events are emitted at key points in the pipeline to allow
observability, logging, and reactive behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Types of pipeline lifecycle events."""

    # World lifecycle
    WORLD_GENERATED = "world.generated"
    WORLD_VALIDATED = "world.validated"
    WORLD_VALIDATION_FAILED = "world.validation_failed"
    WORLD_RESET = "world.reset"

    # Task lifecycle
    TASK_GENERATED = "task.generated"
    TASK_VALIDATED = "task.validated"
    TASK_VALIDATION_FAILED = "task.validation_failed"
    TASK_REJECTED = "task.rejected"

    # Run lifecycle
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_TIMED_OUT = "run.timed_out"
    RUN_CANCELLED = "run.cancelled"

    # Agent events
    AGENT_STEP = "agent.step"
    AGENT_TOOL_CALL = "agent.tool_call"
    AGENT_TOOL_RESULT = "agent.tool_result"
    AGENT_FINISHED = "agent.finished"

    # Verification events
    VERIFICATION_STARTED = "verification.started"
    VERIFICATION_COMPLETED = "verification.completed"
    VERIFICATION_FAILED = "verification.failed"

    # Diagnosis events
    DIAGNOSIS_COMPLETED = "diagnosis.completed"

    # Curriculum events
    CURRICULUM_UPDATED = "curriculum.updated"
    TASK_SELECTED = "task.selected"
    CAPABILITY_UPDATED = "capability.updated"

    # Experiment events
    EXPERIMENT_STARTED = "experiment.started"
    EXPERIMENT_COMPLETED = "experiment.completed"

    # Sandbox events
    SANDBOX_CREATED = "sandbox.created"
    SANDBOX_DESTROYED = "sandbox.destroyed"


@dataclass
class Event:
    """A pipeline lifecycle event.

    Attributes:
        event_type: The type of event.
        timestamp: When the event occurred.
        source: Component that emitted the event.
        data: Event-specific payload.
        event_id: Unique identifier for this event.
    """

    event_type: EventType
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str | None = None
    event_id: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        if self.event_id is None:
            import uuid

            self.event_id = uuid.uuid4().hex[:12]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class EventEmitter:
    """Simple event emitter for pipeline observability.

    Supports synchronous event emission with registered handlers.
    """

    def __init__(self):
        self._handlers: dict[EventType, list] = {}
        self._history: list[Event] = []

    def on(self, event_type: EventType, handler) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The event type to listen for.
            handler: Callable that receives an Event.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event: Event) -> None:
        """Emit an event to all registered handlers.

        Args:
            event: The event to emit.
        """
        self._history.append(event)
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception:
                pass  # Don't let handler errors break the pipeline

    def get_history(self, event_type: EventType | None = None) -> list[Event]:
        """Get event history, optionally filtered by type.

        Args:
            event_type: Optional filter by event type.

        Returns:
            List of events.
        """
        if event_type is None:
            return list(self._history)
        return [e for e in self._history if e.event_type == event_type]

    def clear_history(self) -> None:
        """Clear the event history."""
        self._history.clear()
