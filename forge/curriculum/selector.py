"""Adaptive curriculum engine: selects tasks based on agent performance.

Tracks capability scores and generates targeted tasks for weaknesses.
"""

from __future__ import annotations

import random
from typing import Any

from forge.core.schemas import (
    CurriculumState,
    CurriculumStrategy,
    RunResult,
    TaskSpec,
)


class CapabilityTracker:
    """Tracks per-capability performance estimates.

    For each capability category, records:
    - attempts
    - successes
    - failures
    - confidence estimate
    - recent performance
    """

    def __init__(self):
        self._data: dict[str, dict[str, Any]] = {}

    def record(self, capability: str, success: bool) -> None:
        """Record a run outcome for a capability.

        Args:
            capability: The capability category.
            success: Whether the run succeeded.
        """
        if capability not in self._data:
            self._data[capability] = {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "recent": [],
            }

        data = self._data[capability]
        data["attempts"] += 1
        if success:
            data["successes"] += 1
        else:
            data["failures"] += 1
        data["recent"].append(success)
        # Keep only last 20
        if len(data["recent"]) > 20:
            data["recent"] = data["recent"][-20:]

    def get_score(self, capability: str) -> float:
        """Get the performance score for a capability.

        Args:
            capability: The capability category.

        Returns:
            Score in [0, 1]. Returns 0.5 if no data.
        """
        data = self._data.get(capability)
        if not data or data["attempts"] == 0:
            return 0.5
        return data["successes"] / data["attempts"]

    def get_all_scores(self) -> dict[str, float]:
        """Get scores for all tracked capabilities.

        Returns:
            Dict mapping capability names to scores.
        """
        return {cap: self.get_score(cap) for cap in self._data}

    def get_weaknesses(self, threshold: float = 0.5, min_samples: int = 3) -> list[tuple[str, float]]:
        """Get capabilities below the threshold.

        Args:
            threshold: Minimum acceptable score.
            min_samples: Minimum samples to consider.

        Returns:
            List of (capability, score) tuples sorted by score.
        """
        weaknesses = []
        for cap, data in self._data.items():
            if data["attempts"] >= min_samples:
                score = self.get_score(cap)
                if score < threshold:
                    weaknesses.append((cap, score))
        weaknesses.sort(key=lambda x: x[1])
        return weaknesses

    def get_all_data(self) -> dict[str, dict[str, Any]]:
        """Get all tracking data.

        Returns:
            Raw tracking data.
        """
        return dict(self._data)


class CurriculumSelector:
    """Selects tasks based on the current strategy.

    Supports static, random, and adaptive strategies.
    """

    def __init__(
        self,
        strategy: CurriculumStrategy = CurriculumStrategy.ADAPTIVE,
        capability_tracker: CapabilityTracker | None = None,
    ):
        self.strategy = strategy
        self.tracker = capability_tracker or CapabilityTracker()
        self._history: list[str] = []

    def select(
        self,
        available_tasks: list[TaskSpec],
        num_tasks: int = 1,
    ) -> list[TaskSpec]:
        """Select tasks from the available pool.

        Args:
            available_tasks: List of available tasks.
            num_tasks: Number of tasks to select.

        Returns:
            Selected tasks.
        """
        if not available_tasks:
            return []

        if self.strategy == CurriculumStrategy.STATIC:
            return self._select_static(available_tasks, num_tasks)
        elif self.strategy == CurriculumStrategy.RANDOM:
            return self._select_random(available_tasks, num_tasks)
        else:  # ADAPTIVE
            return self._select_adaptive(available_tasks, num_tasks)

    def _select_static(self, available_tasks: list[TaskSpec], num_tasks: int) -> list[TaskSpec]:
        """Select tasks in order (static curriculum)."""
        return available_tasks[:num_tasks]

    def _select_random(self, available_tasks: list[TaskSpec], num_tasks: int) -> list[TaskSpec]:
        """Select tasks randomly."""
        k = min(num_tasks, len(available_tasks))
        return random.sample(available_tasks, k)

    def _select_adaptive(self, available_tasks: list[TaskSpec], num_tasks: int) -> list[TaskSpec]:
        """Select tasks targeting agent weaknesses.

        Prioritizes tasks that exercise weak capabilities,
        with some exploration for diversity.
        """
        weaknesses = self.tracker.get_weaknesses()
        weak_caps = {w[0] for w in weaknesses}

        if not weak_caps:
            # No known weaknesses, use random
            return self._select_random(available_tasks, num_tasks)

        # Score tasks by how well they target weaknesses
        scored = []
        for task in available_tasks:
            score = 0.0
            for cap in task.capabilities:
                if cap in weak_caps:
                    score += 1.0
            scored.append((task, score))

        # Sort by score descending, then shuffle ties
        scored.sort(key=lambda x: -x[1])

        # Take top tasks, with some randomness
        k = min(num_tasks, len(scored))
        top_tasks = [s[0] for s in scored[: max(k * 2, k)]]
        selected = random.sample(top_tasks, min(k, len(top_tasks)))

        for task in selected:
            self._history.append(task.task_id)

        return selected

    def update(self, result: RunResult) -> None:
        """Update the curriculum based on a run result.

        Args:
            result: The completed run result.
        """
        if not result.verification:
            return

        # Extract capabilities from task metadata
        capabilities = result.metadata.get("capabilities", [])
        if not capabilities:
            # Try to get from trajectory
            if result.trajectory:
                for step in result.trajectory.steps:
                    if step.metadata:
                        capabilities = step.metadata.get("capabilities", [])
                        break

        success = result.verification.passed
        for cap in capabilities:
            self.tracker.record(cap, success)

    def get_state(self) -> CurriculumState:
        """Get the current curriculum state.

        Returns:
            CurriculumState snapshot.
        """
        return CurriculumState(
            strategy=self.strategy,
            capability_scores=self.tracker.get_all_scores(),
        )

    def get_history(self) -> list[str]:
        """Get the task selection history.

        Returns:
            List of selected task IDs.
        """
        return list(self._history)
