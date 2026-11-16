"""Curriculum state updates based on verified run outcomes.

Provides functions to update the curriculum state after each
training cycle based on verified agent performance.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from forge.core.schemas import CurriculumState, CurriculumStrategy, RunResult
from forge.curriculum.capability_tracker import CapabilityTracker


class CurriculumUpdater:
    """Updates curriculum state based on run outcomes.

    After each training cycle, analyzes results and updates:
    - Capability scores
    - Task pool
    - Selected tasks for next cycle
    - Generation counter
    """

    def __init__(
        self,
        state: CurriculumState,
        tracker: CapabilityTracker,
        min_attempts_for_weakness: int = 3,
        weakness_threshold: float = 0.4,
    ):
        self.state = state
        self.tracker = tracker
        self.min_attempts_for_weakness = min_attempts_for_weakness
        self.weakness_threshold = weakness_threshold

    def update_from_results(
        self,
        results: list[RunResult],
        new_task_pool: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update curriculum state from a batch of run results.

        Args:
            results: List of run results from the training cycle.
            new_task_pool: Optional new task pool to use.

        Returns:
            Dictionary with update summary.
        """
        # Update capability tracker
        for result in results:
            capabilities = result.metadata.get("capabilities", [])
            if capabilities:
                self.tracker.update_from_result(result, capabilities)

        # Update capability scores
        self.state.capability_scores = self.tracker.get_scores()

        # Update task pool if provided
        if new_task_pool is not None:
            self.state.task_pool = new_task_pool

        # Select next tasks based on strategy
        self.state.selected_tasks = self._select_next_tasks(results)

        # Increment generation
        self.state.generation += 1
        self.state.updated_at = datetime.utcnow().isoformat()

        return {
            "generation": self.state.generation,
            "capabilities_updated": len(self.tracker.capabilities),
            "weaknesses": self.tracker.get_weaknesses(
                self.weakness_threshold,
                self.min_attempts_for_weakness,
            ),
            "next_tasks": len(self.state.selected_tasks),
            "task_pool_size": len(self.state.task_pool),
        }

    def _select_next_tasks(self, results: list[RunResult]) -> list[str]:
        """Select tasks for the next training cycle.

        Args:
            results: Recent run results.

        Returns:
            List of task IDs for the next cycle.
        """
        strategy = self.state.strategy

        if strategy == CurriculumStrategy.ADAPTIVE:
            return self._adaptive_selection(results)
        elif strategy == CurriculumStrategy.RANDOM:
            return self._random_selection()
        else:
            return self._static_selection()

    def _adaptive_selection(self, results: list[RunResult]) -> list[str]:
        """Select tasks targeting verified weaknesses.

        Args:
            results: Recent run results.

        Returns:
            List of task IDs targeting weaknesses.
        """
        weaknesses = self.tracker.get_weaknesses(
            self.weakness_threshold,
            self.min_attempts_for_weakness,
        )

        if not weaknesses:
            # No weaknesses identified, use random selection
            return self._random_selection()

        # Select tasks that exercise weak capabilities
        selected = []
        for task_id in self.state.task_pool:
            # Check if this task exercises a weak capability
            task_caps = self._get_task_capabilities(task_id)
            if task_caps and any(w in task_caps for w in weaknesses):
                selected.append(task_id)

        # If no matching tasks, fall back to random
        if not selected:
            selected = self._random_selection()

        return selected[:5]  # Limit to 5 tasks per cycle

    def _random_selection(self) -> list[str]:
        """Randomly select tasks from the pool.

        Returns:
            List of randomly selected task IDs.
        """
        import random

        if not self.state.task_pool:
            return []

        pool = list(self.state.task_pool)
        random.shuffle(pool)
        return pool[:5]

    def _static_selection(self) -> list[str]:
        """Select tasks in a fixed order.

        Returns:
            List of task IDs in order.
        """
        return self.state.task_pool[:5]

    def _get_task_capabilities(self, task_id: str) -> list[str]:
        """Get capabilities for a task.

        Args:
            task_id: Task identifier.

        Returns:
            List of capability names.
        """
        # This would normally query a task database
        # For now, return empty list
        return []

    def get_state_summary(self) -> dict[str, Any]:
        """Get a summary of the current curriculum state.

        Returns:
            Dictionary with state summary.
        """
        return {
            "generation": self.state.generation,
            "strategy": self.state.strategy.value,
            "capability_scores": self.state.capability_scores,
            "task_pool_size": len(self.state.task_pool),
            "selected_tasks": len(self.state.selected_tasks),
            "weaknesses": self.tracker.get_weaknesses(
                self.weakness_threshold,
                self.min_attempts_for_weakness,
            ),
            "updated_at": self.state.updated_at,
        }
