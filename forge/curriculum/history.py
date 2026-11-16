"""Curriculum decision history logging.

Records why each task was selected and how the curriculum
evolved over time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class CurriculumDecision:
    """A single curriculum decision record.

    Attributes:
        generation: Curriculum generation number.
        selected_task_id: Task that was selected.
        strategy: Selection strategy used.
        reason: Why this task was selected.
        capability_scores: Capability scores at selection time.
        timestamp: When the decision was made.
    """

    def __init__(
        self,
        generation: int,
        selected_task_id: str,
        strategy: str,
        reason: str,
        capability_scores: dict[str, float] | None = None,
    ):
        self.generation = generation
        self.selected_task_id = selected_task_id
        self.strategy = strategy
        self.reason = reason
        self.capability_scores = capability_scores or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Export decision as dictionary.

        Returns:
            Dictionary with decision data.
        """
        return {
            "generation": self.generation,
            "selected_task_id": self.selected_task_id,
            "strategy": self.strategy,
            "reason": self.reason,
            "capability_scores": self.capability_scores,
            "timestamp": self.timestamp,
        }


class CurriculumHistory:
    """Logs the history of curriculum decisions.

    Maintains an ordered list of CurriculumDecision objects
    and provides methods to query and export the history.
    """

    def __init__(self):
        self.decisions: list[CurriculumDecision] = []

    def record(
        self,
        generation: int,
        selected_task_id: str,
        strategy: str,
        reason: str,
        capability_scores: dict[str, float] | None = None,
    ) -> None:
        """Record a curriculum decision.

        Args:
            generation: Curriculum generation number.
            selected_task_id: Task that was selected.
            strategy: Selection strategy used.
            reason: Why this task was selected.
            capability_scores: Capability scores at selection time.
        """
        decision = CurriculumDecision(
            generation=generation,
            selected_task_id=selected_task_id,
            strategy=strategy,
            reason=reason,
            capability_scores=capability_scores,
        )
        self.decisions.append(decision)

    def get_decisions_for_generation(self, generation: int) -> list[CurriculumDecision]:
        """Get all decisions for a specific generation.

        Args:
            generation: Generation number.

        Returns:
            List of decisions for that generation.
        """
        return [d for d in self.decisions if d.generation == generation]

    def get_decisions_for_task(self, task_id: str) -> list[CurriculumDecision]:
        """Get all decisions for a specific task.

        Args:
            task_id: Task identifier.

        Returns:
            List of decisions for that task.
        """
        return [d for d in self.decisions if d.selected_task_id == task_id]

    def get_strategy_distribution(self) -> dict[str, int]:
        """Get the distribution of strategies used.

        Returns:
            Dictionary mapping strategy names to counts.
        """
        distribution = {}
        for decision in self.decisions:
            distribution[decision.strategy] = distribution.get(decision.strategy, 0) + 1
        return distribution

    def get_task_selection_count(self) -> dict[str, int]:
        """Get how many times each task was selected.

        Returns:
            Dictionary mapping task IDs to selection counts.
        """
        counts = {}
        for decision in self.decisions:
            counts[decision.selected_task_id] = counts.get(decision.selected_task_id, 0) + 1
        return counts

    def get_recent_decisions(self, count: int = 10) -> list[CurriculumDecision]:
        """Get the most recent decisions.

        Args:
            count: Number of recent decisions to return.

        Returns:
            List of recent decisions.
        """
        return self.decisions[-count:]

    def to_dict(self) -> dict[str, Any]:
        """Export full history as dictionary.

        Returns:
            Dictionary with all decisions.
        """
        return {
            "total_decisions": len(self.decisions),
            "strategy_distribution": self.get_strategy_distribution(),
            "task_selection_count": self.get_task_selection_count(),
            "decisions": [d.to_dict() for d in self.decisions],
        }
