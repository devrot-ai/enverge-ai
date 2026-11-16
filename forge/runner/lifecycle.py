"""Run lifecycle state management.

Tracks the state of agent runs through their lifecycle,
handling transitions, timeouts, and interruptions.
"""

from __future__ import annotations

import time
from datetime import datetime
from enum import Enum
from typing import Any

from forge.core.schemas import RunConfig, RunStatus


class RunState(str, Enum):
    """Internal run state for lifecycle management."""

    CREATED = "created"
    WORKSPACE_INITIALIZED = "workspace_initialized"
    SANDBOX_STARTED = "sandbox_started"
    AGENT_RUNNING = "agent_running"
    AGENT_COMPLETED = "agent_completed"
    VERIFYING = "verifying"
    DIAGNOSING = "diagnosing"
    ARTIFACTS_STORED = "artifacts_stored"
    CLEANED_UP = "cleaned_up"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class RunLifecycle:
    """Manages the lifecycle state of a single run.

    Tracks state transitions, timestamps, and metadata
    for each phase of an agent run.
    """

    def __init__(self, run_config: RunConfig):
        self.run_config = run_config
        self.state = RunState.CREATED
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.state_history: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.metadata: dict[str, Any] = {}
        self._record_state(RunState.CREATED)

    def transition(self, new_state: RunState, metadata: dict[str, Any] | None = None) -> None:
        """Transition to a new state.

        Args:
            new_state: The new state to transition to.
            metadata: Optional metadata to record with the transition.

        Raises:
            ValueError: If the transition is invalid.
        """
        self.state = new_state
        self._record_state(new_state, metadata)

    def _record_state(self, state: RunState, metadata: dict[str, Any] | None = None) -> None:
        """Record a state transition."""
        entry = {
            "state": state.value,
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_seconds": (time.time() - self.start_time) if self.start_time else 0.0,
        }
        if metadata:
            entry["metadata"] = metadata
        self.state_history.append(entry)

    def start(self) -> None:
        """Mark the run as started."""
        self.start_time = time.time()
        self.transition(RunState.WORKSPACE_INITIALIZED)

    def mark_agent_running(self) -> None:
        """Mark that the agent has started executing."""
        self.transition(RunState.AGENT_RUNNING)

    def mark_agent_completed(self) -> None:
        """Mark that the agent has finished executing."""
        self.transition(RunState.AGENT_COMPLETED)

    def mark_verifying(self) -> None:
        """Mark that verification has started."""
        self.transition(RunState.VERIFYING)

    def mark_diagnosing(self) -> None:
        """Mark that diagnosis has started."""
        self.transition(RunState.DIAGNOSING)

    def mark_complete(self) -> None:
        """Mark the run as fully complete."""
        self.end_time = time.time()
        self.transition(RunState.ARTIFACTS_STORED)
        self.transition(RunState.CLEANED_UP)

    def mark_failed(self, error: str) -> None:
        """Mark the run as failed.

        Args:
            error: Error message describing the failure.
        """
        self.end_time = time.time()
        self.errors.append(error)
        self.transition(RunState.FAILED, {"error": error})

    def mark_cancelled(self) -> None:
        """Mark the run as cancelled."""
        self.end_time = time.time()
        self.transition(RunState.CANCELLED)

    def mark_timed_out(self) -> None:
        """Mark the run as timed out."""
        self.end_time = time.time()
        error = f"Run timed out after {self.run_config.timeout_seconds}s"
        self.errors.append(error)
        self.transition(RunState.TIMED_OUT, {"timeout_seconds": self.run_config.timeout_seconds})

    def check_timeout(self) -> bool:
        """Check if the run has exceeded its timeout.

        Returns:
            True if the run has timed out.
        """
        if self.start_time is None:
            return False
        elapsed = time.time() - self.start_time
        return elapsed > self.run_config.timeout_seconds

    def get_duration(self) -> float:
        """Get the run duration in seconds.

        Returns:
            Duration in seconds, or 0 if not started.
        """
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def get_status(self) -> RunStatus:
        """Map internal state to RunStatus enum.

        Returns:
            RunStatus corresponding to current state.
        """
        state_map = {
            RunState.CREATED: RunStatus.PENDING,
            RunState.WORKSPACE_INITIALIZED: RunStatus.RUNNING,
            RunState.SANDBOX_STARTED: RunStatus.RUNNING,
            RunState.AGENT_RUNNING: RunStatus.RUNNING,
            RunState.AGENT_COMPLETED: RunStatus.COMPLETED,
            RunState.VERIFYING: RunStatus.COMPLETED,
            RunState.DIAGNOSING: RunStatus.COMPLETED,
            RunState.ARTIFACTS_STORED: RunStatus.COMPLETED,
            RunState.CLEANED_UP: RunStatus.COMPLETED,
            RunState.FAILED: RunStatus.FAILED,
            RunState.CANCELLED: RunStatus.CANCELLED,
            RunState.TIMED_OUT: RunStatus.TIMED_OUT,
        }
        return state_map.get(self.state, RunStatus.PENDING)

    def is_terminal(self) -> bool:
        """Check if the run is in a terminal state.

        Returns:
            True if the run has reached a final state.
        """
        return self.state in (
            RunState.CLEANED_UP,
            RunState.FAILED,
            RunState.CANCELLED,
            RunState.TIMED_OUT,
        )

    def to_dict(self) -> dict[str, Any]:
        """Export lifecycle state as a dictionary.

        Returns:
            Dictionary with lifecycle information.
        """
        return {
            "run_id": self.run_config.run_id,
            "state": self.state.value,
            "status": self.get_status().value,
            "duration_seconds": self.get_duration(),
            "state_history": self.state_history,
            "errors": self.errors,
            "is_terminal": self.is_terminal(),
        }
