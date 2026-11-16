"""Automatic difficulty scaling for adaptive curriculum.

Adjusts task difficulty based on recent agent performance.
If pass rate is high, difficulty increases. If low, it decreases.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DifficultyAdjustment:
    """Result of a difficulty adjustment."""

    agent_type: str
    template_name: str
    old_difficulty: int
    new_difficulty: int
    pass_rate: float
    recent_runs: int
    action: str = ""  # "increase", "decrease", "maintain"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_type": self.agent_type,
            "template_name": self.template_name,
            "old_difficulty": self.old_difficulty,
            "new_difficulty": self.new_difficulty,
            "pass_rate": round(self.pass_rate, 4),
            "recent_runs": self.recent_runs,
            "action": self.action,
        }


class AutoScaler:
    """Automatically adjust task difficulty based on agent performance.

    Uses a sliding window of recent runs per agent-template pair.
    - Pass rate > 80% → increase difficulty
    - Pass rate < 20% → decrease difficulty
    - 20-80% → maintain current difficulty
    - Difficulty capped at 1-5
    """

    def __init__(
        self,
        window_size: int = 10,
        high_threshold: float = 0.8,
        low_threshold: float = 0.2,
        min_difficulty: int = 1,
        max_difficulty: int = 5,
    ):
        """Initialize the auto-scaler.

        Args:
            window_size: Number of recent runs to consider.
            high_threshold: Pass rate above which difficulty increases.
            low_threshold: Pass rate below which difficulty decreases.
            min_difficulty: Minimum difficulty level.
            max_difficulty: Maximum difficulty level.
        """
        self.window_size = window_size
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.min_difficulty = min_difficulty
        self.max_difficulty = max_difficulty
        # History: (agent_type, template_name) → list of (passed: bool)
        self._history: dict[tuple[str, str], list[bool]] = {}

    def record_result(
        self,
        agent_type: str,
        template_name: str,
        passed: bool,
    ) -> None:
        """Record a run result for difficulty tracking.

        Args:
            agent_type: Agent type name.
            template_name: Template name.
            passed: Whether the run passed.
        """
        key = (agent_type, template_name)
        if key not in self._history:
            self._history[key] = []
        self._history[key].append(passed)
        # Keep only the most recent results
        if len(self._history[key]) > self.window_size:
            self._history[key] = self._history[key][-self.window_size :]

    def adjust_difficulty(
        self,
        agent_type: str,
        template_name: str,
        current_difficulty: int,
    ) -> DifficultyAdjustment:
        """Adjust difficulty based on recent performance.

        Args:
            agent_type: Agent type name.
            template_name: Template name.
            current_difficulty: Current difficulty level.

        Returns:
            DifficultyAdjustment with new difficulty and reason.
        """
        key = (agent_type, template_name)
        history = self._history.get(key, [])

        if len(history) == 0:
            return DifficultyAdjustment(
                agent_type=agent_type,
                template_name=template_name,
                old_difficulty=current_difficulty,
                new_difficulty=current_difficulty,
                pass_rate=0.0,
                recent_runs=0,
                action="maintain",
            )

        pass_rate = sum(history) / len(history)
        action = "maintain"
        new_difficulty = current_difficulty

        if pass_rate >= self.high_threshold:
            action = "increase"
            new_difficulty = min(current_difficulty + 1, self.max_difficulty)
        elif pass_rate <= self.low_threshold:
            action = "decrease"
            new_difficulty = max(current_difficulty - 1, self.min_difficulty)

        adjustment = DifficultyAdjustment(
            agent_type=agent_type,
            template_name=template_name,
            old_difficulty=current_difficulty,
            new_difficulty=new_difficulty,
            pass_rate=pass_rate,
            recent_runs=len(history),
            action=action,
        )

        logger.info(
            f"Auto-scale {agent_type}/{template_name}: "
            f"{current_difficulty} → {new_difficulty} "
            f"(pass rate {pass_rate:.0%}, {len(history)} runs)"
        )

        return adjustment

    def get_pass_rate(
        self,
        agent_type: str,
        template_name: str,
    ) -> float:
        """Get current pass rate for an agent-template pair.

        Args:
            agent_type: Agent type name.
            template_name: Template name.

        Returns:
            Pass rate between 0 and 1.
        """
        key = (agent_type, template_name)
        history = self._history.get(key, [])
        if not history:
            return 0.0
        return sum(history) / len(history)

    def get_history_size(
        self,
        agent_type: str,
        template_name: str,
    ) -> int:
        """Get number of recorded runs for an agent-template pair.

        Args:
            agent_type: Agent type name.
            template_name: Template name.

        Returns:
            Number of recorded runs.
        """
        key = (agent_type, template_name)
        return len(self._history.get(key, []))

    def reset(
        self,
        agent_type: str | None = None,
        template_name: str | None = None,
    ) -> None:
        """Reset difficulty history.

        Args:
            agent_type: If provided, reset only for this agent.
            template_name: If provided, reset only for this template.
        """
        if agent_type is None and template_name is None:
            self._history.clear()
            return

        keys_to_remove = []
        for key in self._history:
            a, t = key
            if agent_type and a == agent_type:
                keys_to_remove.append(key)
            if template_name and t == template_name:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._history[key]

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            key: value
            for key, value in self._history.items()
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Load state from dictionary.

        Args:
            data: Serialized state.
        """
        self._history = {
            tuple(key.split(",", 1)): value
            for key, value in data.items()
        }
