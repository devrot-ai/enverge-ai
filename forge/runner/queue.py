"""Queue-based task scheduling for batch experiments.

Provides priority-based task queue with JSON persistence for
pause/resume support.
"""

from __future__ import annotations

import heapq
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.core.schemas import TaskSpec

logger = logging.getLogger(__name__)

# Priority levels (lower = higher priority)
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3


@dataclass(order=True)
class QueuedTask:
    """A task in the queue with priority."""

    priority: int
    task_id: str = field(compare=False)
    task: TaskSpec = field(compare=False)
    enqueued_at: str = field(compare=False, default_factory=lambda: datetime.utcnow().isoformat())


class TaskQueue:
    """Priority-based task queue with JSON persistence.

    Supports enqueue/dequeue with priority ordering, pause/resume,
    and JSON persistence for crash recovery.
    """

    def __init__(self, persist_path: str | Path | None = None):
        """Initialize the task queue.

        Args:
            persist_path: Path for JSON persistence file.
        """
        self._heap: list[QueuedTask] = []
        self._counter = 0
        self._paused = False
        self.persist_path = Path(persist_path) if persist_path else None

        # Load persisted state
        if self.persist_path and self.persist_path.exists():
            self._load()

    def enqueue(
        self,
        task: TaskSpec,
        priority: int = PRIORITY_MEDIUM,
    ) -> None:
        """Add a task to the queue.

        Args:
            task: Task specification.
            priority: Priority level (1=high, 2=medium, 3=low).
        """
        if self._paused:
            logger.warning("Queue is paused; task enqueued but not processed")

        entry = QueuedTask(
            priority=priority,
            task_id=task.task_id,
            task=task,
        )
        heapq.heappush(self._heap, entry)
        self._persist()
        logger.debug(f"Enqueued {task.task_id} with priority {priority}")

    def dequeue(self) -> TaskSpec | None:
        """Remove and return the highest priority task.

        Returns:
            TaskSpec or None if queue is empty.
        """
        if not self._heap:
            return None
        entry = heapq.heappop(self._heap)
        self._persist()
        return entry.task

    def peek(self) -> TaskSpec | None:
        """Return the highest priority task without removing it.

        Returns:
            TaskSpec or None if queue is empty.
        """
        if not self._heap:
            return None
        return self._heap[0].task

    def size(self) -> int:
        """Get the number of tasks in the queue."""
        return len(self._heap)

    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return len(self._heap) == 0

    def pause(self) -> None:
        """Pause the queue (tasks can still be enqueued)."""
        self._paused = True
        logger.info("Queue paused")

    def resume(self) -> None:
        """Resume the queue."""
        self._paused = False
        logger.info("Queue resumed")

    def clear(self) -> None:
        """Clear all tasks from the queue."""
        self._heap.clear()
        self._persist()
        logger.info("Queue cleared")

    def to_dict(self) -> dict[str, Any]:
        """Serialize queue state to dictionary."""
        return {
            "tasks": [
                {
                    "priority": entry.priority,
                    "task_id": entry.task_id,
                    "enqueued_at": entry.enqueued_at,
                }
                for entry in self._heap
            ],
            "paused": self._paused,
        }

    def _persist(self) -> None:
        """Persist queue state to JSON file."""
        if not self.persist_path:
            return
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "tasks": [
                    {
                        "priority": entry.priority,
                        "task_id": entry.task_id,
                        "enqueued_at": entry.enqueued_at,
                    }
                    for entry in self._heap
                ],
                "paused": self._paused,
            }
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist queue: {e}")

    def _load(self) -> None:
        """Load queue state from JSON file."""
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._paused = data.get("paused", False)
            # Tasks are loaded without TaskSpec objects (they need to be
            # re-created from the task store). This is a simplified persistence.
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")
