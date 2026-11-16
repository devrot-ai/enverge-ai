"""Reward signal computation for training data.

Computes reward signals for agent runs based on pass/fail status,
difficulty level, static analysis results, and other factors.
Used for training data quality scoring and RL reward signals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from forge.core.schemas import RunResult, TaskSpec

logger = logging.getLogger(__name__)


@dataclass
class RewardSignal:
    """Reward signal for a single run.

    Contains the total reward and individual component rewards
    with explanations for each component.
    """

    total_reward: float = 0.0
    components: dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    run_id: str = ""
    task_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "total_reward": round(self.total_reward, 4),
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "explanation": self.explanation,
        }


class RewardComputer:
    """Compute reward signals for agent runs.

    Calculates rewards based on:
    - Pass/fail status (primary signal)
    - Public test pass rate (partial credit)
    - Hidden test pass rate (bonus)
    - Static analysis pass (bonus)
    - Difficulty weight (harder tasks = higher reward)
    - Regression penalty (if performance regressed)

    Pluggable via subclassing for custom reward functions.
    """

    # Reward weights
    PASS_REWARD = 1.0
    FAIL_REWARD = -0.5
    PUBLIC_TEST_WEIGHT = 0.3
    HIDDEN_TEST_BONUS = 0.2
    STATIC_ANALYSIS_BONUS = 0.1
    DIFFICULTY_MULTIPLIER = 0.1
    REGRESSION_PENALTY = -0.3

    def __init__(self, weights: dict[str, float] | None = None):
        """Initialize the reward computer.

        Args:
            weights: Optional override for reward weights.
        """
        if weights:
            for key, value in weights.items():
                attr = key.upper()
                if hasattr(self, attr):
                    setattr(self, attr, value)

    def compute(self, run_result: RunResult, task_spec: TaskSpec) -> RewardSignal:
        """Compute reward signal for a run.

        Args:
            run_result: Run result with pass/fail and verification data.
            task_spec: Task specification with difficulty and metadata.

        Returns:
            RewardSignal with total reward and components.
        """
        components: dict[str, float] = {}
        explanations: list[str] = []

        # Primary pass/fail reward
        if run_result.passed:
            components["pass_fail"] = self.PASS_REWARD
            explanations.append(f"Passed: +{self.PASS_REWARD}")
        else:
            components["pass_fail"] = self.FAIL_REWARD
            explanations.append(f"Failed: {self.FAIL_REWARD}")

        # Public test partial credit
        if run_result.verification and run_result.verification.public_tests_passed:
            components["public_tests"] = self.PUBLIC_TEST_WEIGHT
            explanations.append(
                f"Public tests passed: +{self.PUBLIC_TEST_WEIGHT}"
            )

        # Hidden test bonus
        if run_result.verification and run_result.verification.hidden_tests_passed:
            components["hidden_tests"] = self.HIDDEN_TEST_BONUS
            explanations.append(
                f"Hidden tests passed: +{self.HIDDEN_TEST_BONUS}"
            )

        # Regression test bonus
        if run_result.verification and run_result.verification.regression_tests_passed:
            components["regression_tests"] = self.STATIC_ANALYSIS_BONUS
            explanations.append(
                f"Regression tests passed: +{self.STATIC_ANALYSIS_BONUS}"
            )

        # Difficulty weight
        difficulty = task_spec.difficulty_level or 1
        difficulty_weight = 1.0 + (difficulty - 1) * self.DIFFICULTY_MULTIPLIER
        components["difficulty_weight"] = difficulty_weight - 1.0
        explanations.append(f"Difficulty {difficulty}: x{difficulty_weight:.2f} multiplier")

        # Regression penalty (if previous baseline exists)
        if run_result.metadata and run_result.metadata.get("regression_detected"):
            components["regression"] = self.REGRESSION_PENALTY
            explanations.append(f"Regression detected: {self.REGRESSION_PENALTY}")

        # Calculate total reward
        base_reward = sum(components.values())
        total_reward = base_reward * difficulty_weight

        reward = RewardSignal(
            total_reward=total_reward,
            components=components,
            explanation="; ".join(explanations),
            run_id=run_result.run_id,
            task_id=task_spec.task_id,
        )

        return reward

    def compute_batch(
        self,
        run_results: list[RunResult],
        task_specs: list[TaskSpec],
    ) -> list[RewardSignal]:
        """Compute rewards for a batch of runs.

        Args:
            run_results: List of run results.
            task_specs: List of task specifications.

        Returns:
            List of reward signals.
        """
        rewards = []
        for run_result, task_spec in zip(run_results, task_specs):
            try:
                reward = self.compute(run_result, task_spec)
                rewards.append(reward)
            except Exception as e:
                logger.error(
                    f"Error computing reward for {run_result.run_id}: {e}"
                )
                rewards.append(
                    RewardSignal(
                        total_reward=0.0,
                        run_id=run_result.run_id,
                        task_id=task_spec.task_id,
                        explanation=f"Error: {e}",
                    )
                )
        return rewards

    def average_reward(self, rewards: list[RewardSignal]) -> float:
        """Calculate average reward across a list of rewards.

        Args:
            rewards: List of reward signals.

        Returns:
            Average total reward.
        """
        if not rewards:
            return 0.0
        return sum(r.total_reward for r in rewards) / len(rewards)
