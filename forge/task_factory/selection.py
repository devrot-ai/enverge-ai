"""Task pool management and selection.

Provides functions to manage the task pool and select tasks
for training cycles.
"""

from __future__ import annotations

import random
from typing import Any


class TaskPool:
    """Manages a pool of available tasks.

    Tracks which tasks are available, selected, and completed.
    Provides selection strategies for different curriculum modes.

    Attributes:
        tasks: Dictionary of task_id -> task metadata.
        selected: Set of currently selected task IDs.
        completed: Set of completed task IDs.
    """

    def __init__(self):
        self.tasks: dict[str, dict[str, Any]] = {}
        self.selected: set[str] = set()
        self.completed: set[str] = set()

    def add_task(self, task_id: str, metadata: dict[str, Any]) -> None:
        """Add a task to the pool.

        Args:
            task_id: Task identifier.
            metadata: Task metadata dictionary.
        """
        self.tasks[task_id] = metadata

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the pool.

        Args:
            task_id: Task identifier.

        Returns:
            True if task was removed.
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self.selected.discard(task_id)
            self.completed.discard(task_id)
            return True
        return False

    def mark_completed(self, task_id: str) -> None:
        """Mark a task as completed.

        Args:
            task_id: Task identifier.
        """
        self.completed.add(task_id)
        self.selected.discard(task_id)

    def get_available_tasks(self) -> list[str]:
        """Get list of available (not completed) task IDs.

        Returns:
            List of available task IDs.
        """
        return [tid for tid in self.tasks if tid not in self.completed]

    def select_random(self, count: int = 1) -> list[str]:
        """Randomly select tasks from the pool.

        Args:
            count: Number of tasks to select.

        Returns:
            List of selected task IDs.
        """
        available = self.get_available_tasks()
        selected = random.sample(available, min(count, len(available)))
        self.selected = set(selected)
        return selected

    def select_by_capability(
        self,
        capability: str,
        count: int = 1,
    ) -> list[str]:
        """Select tasks that exercise a specific capability.

        Args:
            capability: Capability name.
            count: Number of tasks to select.

        Returns:
            List of selected task IDs.
        """
        matching = [
            tid
            for tid, meta in self.tasks.items()
            if tid not in self.completed and capability in meta.get("capabilities", [])
        ]
        random.shuffle(matching)
        selected = matching[:count]
        self.selected = set(selected)
        return selected

    def select_by_difficulty(
        self,
        min_difficulty: int = 1,
        max_difficulty: int = 5,
        count: int = 1,
    ) -> list[str]:
        """Select tasks within a difficulty range.

        Args:
            min_difficulty: Minimum difficulty.
            max_difficulty: Maximum difficulty.
            count: Number of tasks to select.

        Returns:
            List of selected task IDs.
        """
        matching = [
            tid
            for tid, meta in self.tasks.items()
            if tid not in self.completed and min_difficulty <= meta.get("difficulty_level", 1) <= max_difficulty
        ]
        random.shuffle(matching)
        selected = matching[:count]
        self.selected = set(selected)
        return selected

    def select_diverse(self, count: int = 5) -> list[str]:
        """Select a diverse set of tasks.

        Tries to select tasks covering different capabilities
        and difficulty levels.

        Args:
            count: Number of tasks to select.

        Returns:
            List of selected task IDs.
        """
        available = self.get_available_tasks()
        if not available:
            return []

        # Sort by difficulty to get a spread
        sorted_tasks = sorted(
            available,
            key=lambda tid: self.tasks[tid].get("difficulty_level", 1),
        )

        # Select evenly spaced tasks
        step = max(1, len(sorted_tasks) // count)
        selected = sorted_tasks[::step][:count]
        self.selected = set(selected)
        return selected

    def get_pool_stats(self) -> dict[str, Any]:
        """Get statistics about the task pool.

        Returns:
            Dictionary with pool statistics.
        """
        return {
            "total_tasks": len(self.tasks),
            "available": len(self.get_available_tasks()),
            "selected": len(self.selected),
            "completed": len(self.completed),
        }

    def to_dict(self) -> dict[str, Any]:
        """Export pool state as dictionary.

        Returns:
            Dictionary with pool state.
        """
        return {
            "tasks": self.tasks,
            "selected": list(self.selected),
            "completed": list(self.completed),
            "stats": self.get_pool_stats(),
        }
