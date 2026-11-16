"""Training adapter interface for future RL integration.

Provides a clean adapter interface for connecting ForgeLab's
environment and evaluation layer to external RL trainers like
Hugging Face TRL, GRPO, PPO, or Microsoft Agent Lightning.

This is a preparation interface — model-weight training is not
part of v0.1. The adapter normalizes trajectory export so the
training backend can be replaced without rewriting the environment factory.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.core.schemas import RunResult, TaskCategory, FailureCategory


class TrainingAdapter(ABC):
    """Abstract base class for training adapters.

    Subclasses implement the interface to connect ForgeLab
    trajectories to external training frameworks.
    """

    @abstractmethod
    def prepare_training_data(
        self,
        results: list[RunResult],
    ) -> list[dict[str, Any]]:
        """Prepare training data from run results.

        Args:
            results: List of run results.

        Returns:
            List of training examples in the framework's format.
        """
        raise NotImplementedError

    @abstractmethod
    def compute_reward(self, result: RunResult) -> float:
        """Compute reward signal for a run result.

        Args:
            result: The run result.

        Returns:
            Reward value.
        """
        raise NotImplementedError

    @abstractmethod
    def train(
        self,
        training_data: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a training step.

        Args:
            training_data: Prepared training data.
            **kwargs: Framework-specific training parameters.

        Returns:
            Training metrics.
        """
        raise NotImplementedError


class TrajectoryExporter:
    """Exports trajectories in a normalized format for training.

    Converts ForgeLab run results into a standardized format
    that can be consumed by various training frameworks.
    """

    def export_trajectory(
        self,
        result: RunResult,
        include_tokens: bool = True,
    ) -> dict[str, Any]:
        """Export a single run as a training example.

        Args:
            result: The run result.
            include_tokens: Whether to include token usage data.

        Returns:
            Dictionary with normalized trajectory data.
        """
        trajectory = result.trajectory
        if trajectory is None:
            return {}

        steps = []
        for step in trajectory.steps:
            step_data = {
                "step_index": step.step_index,
                "observation": step.observation,
                "action": step.action,
                "tool_name": step.tool_name,
                "tool_arguments": step.tool_arguments,
                "tool_result": step.tool_result,
                "duration_seconds": step.duration_seconds,
                "error": step.error,
            }
            if include_tokens and step.metadata:
                step_data["token_usage"] = step.metadata.get("token_usage", {})
            steps.append(step_data)

        return {
            "task_metadata": {
                "task_id": result.task_id,
                "world_id": result.metadata.get("world_id"),
                "category": result.metadata.get("category"),
                "difficulty_level": result.metadata.get("difficulty_level"),
                "capabilities": result.metadata.get("capabilities", []),
            },
            "model_metadata": {
                "model_identifier": result.metadata.get("model_identifier"),
                "agent_id": result.agent_id,
            },
            "prompt": result.metadata.get("system_prompt", ""),
            "observations": [s["observation"] for s in steps],
            "actions": [s["action"] for s in steps],
            "tool_interactions": [
                {
                    "tool_name": s["tool_name"],
                    "arguments": s["tool_arguments"],
                    "result": s["tool_result"],
                }
                for s in steps
                if s["tool_name"]
            ],
            "final_outcome": {
                "passed": result.passed,
                "agent_believes_success": result.agent_believes_success,
                "verification": result.verification.to_dict() if result.verification else None,
                "failure_diagnosis": result.diagnosis.to_dict() if result.diagnosis else None,
            },
            "reward_components": self._compute_reward_components(result),
            "environment_version": result.metadata.get("environment_version", "0.1"),
            "random_seed": result.metadata.get("seed"),
        }

    def _compute_reward_components(
        self, result: RunResult, difficulty_weight: bool = False
    ) -> dict[str, float]:
        """Compute reward components for a run result.

        Args:
            result: The run result.
            difficulty_weight: Whether to weight reward by task difficulty.

        Returns:
            Dictionary with reward components.
        """
        reward = 0.0
        components = {}

        # Get difficulty level (default 1)
        difficulty = result.metadata.get("difficulty_level", 1)
        if isinstance(difficulty, str):
            try:
                difficulty = int(difficulty)
            except (ValueError, TypeError):
                difficulty = 1
        difficulty = max(1, min(5, difficulty))

        # Task completion reward (weighted by difficulty)
        if result.passed:
            base = 1.0
            if difficulty_weight:
                base *= (difficulty / 5.0) * 2  # Range: 0.4 - 2.0
            reward += base
            components["task_completion"] = round(base, 4)
        else:
            components["task_completion"] = 0.0

        # Existing tests still pass
        if result.verification and result.verification.existing_tests_passed:
            reg_reward = 0.2
            if difficulty_weight:
                reg_reward *= difficulty / 3.0
            reward += reg_reward
            components["regression_preserved"] = round(reg_reward, 4)
        else:
            components["regression_preserved"] = 0.0

        # Step efficiency (penalize long trajectories)
        if result.trajectory:
            step_count = len(result.trajectory.steps)
            efficiency = max(0.0, 1.0 - step_count / 100.0)
            eff_reward = efficiency * 0.1
            if difficulty_weight:
                eff_reward *= difficulty / 3.0
            reward += eff_reward
            components["step_efficiency"] = round(eff_reward, 4)
        else:
            components["step_efficiency"] = 0.0

        # Difficulty bonus for passing hard tasks
        if difficulty_weight and result.passed and difficulty >= 4:
            bonus = (difficulty - 3) * 0.1
            reward += bonus
            components["difficulty_bonus"] = round(bonus, 4)
        elif difficulty_weight:
            components["difficulty_bonus"] = 0.0

        components["total_reward"] = round(reward, 4)
        return components

    def export_batch(
        self,
        results: list[RunResult],
        output_file: Path | None = None,
    ) -> list[dict[str, Any]]:
        """Export a batch of results as training data.

        Args:
            results: List of run results.
            output_file: Optional file to save JSONL output.

        Returns:
            List of exported trajectory dictionaries.
        """
        exported = []
        for result in results:
            data = self.export_trajectory(result)
            if data:
                exported.append(data)

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                for item in exported:
                    f.write(json.dumps(item, default=str) + "\n")

        return exported


class NoOpTrainingAdapter(TrainingAdapter):
    """No-operation training adapter for v0.1.

    This adapter does not perform actual training. It exists
    to provide a valid interface while model-weight training
    is not yet implemented.
    """

    def prepare_training_data(
        self,
        results: list[RunResult],
    ) -> list[dict[str, Any]]:
        """Export trajectories without preparing for training.

        Args:
            results: List of run results.

        Returns:
            List of exported trajectory dictionaries.
        """
        exporter = TrajectoryExporter()
        return exporter.export_batch(results)

    def compute_reward(self, result: RunResult) -> float:
        """Compute a simple reward based on pass/fail.

        Args:
            result: The run result.

        Returns:
            Reward value (1.0 for pass, 0.0 for fail).
        """
        exporter = TrajectoryExporter()
        components = exporter._compute_reward_components(result)
        return components.get("total_reward", 0.0)

    def train(
        self,
        training_data: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """No-op training — returns metadata only.

        Args:
            training_data: Prepared training data.
            **kwargs: Ignored.

        Returns:
            Dictionary indicating no training was performed.
        """
        return {
            "adapter": "NoOpTrainingAdapter",
            "training_data_size": len(training_data),
            "message": "Model-weight training not implemented in v0.1",
            "timestamp": datetime.utcnow().isoformat(),
        }


class TrajectoryFilter:
    """Filter trajectories by quality, outcome, or failure category.

    Enables selecting high-quality training data from run results
    based on various criteria.
    """

    def filter(
        self,
        results: list[RunResult],
        passed_only: bool | None = None,
        min_reward: float | None = None,
        failure_category: FailureCategory | None = None,
        category: TaskCategory | None = None,
        min_difficulty: int | None = None,
        max_difficulty: int | None = None,
        max_steps: int | None = None,
    ) -> list[RunResult]:
        """Filter run results by various criteria.

        Args:
            results: List of run results to filter.
            passed_only: If True, only passed runs. If False, only failed.
            min_reward: Minimum total reward threshold.
            failure_category: Only runs with this failure category.
            category: Only runs with this task category.
            min_difficulty: Minimum difficulty level.
            max_difficulty: Maximum difficulty level.
            max_steps: Maximum trajectory steps.

        Returns:
            Filtered list of run results.
        """
        filtered = results
        exporter = TrajectoryExporter()

        if passed_only is not None:
            filtered = [r for r in filtered if r.passed == passed_only]

        if min_reward is not None:
            def has_min_reward(r):
                components = exporter._compute_reward_components(r)
                return components.get("total_reward", 0.0) >= min_reward
            filtered = [r for r in filtered if has_min_reward(r)]

        if failure_category is not None:
            filtered = [
                r for r in filtered
                if r.diagnosis and r.diagnosis.category == failure_category
            ]

        if category is not None:
            filtered = [
                r for r in filtered
                if r.metadata.get("category") == category
            ]

        if min_difficulty is not None:
            def get_diff(r):
                d = r.metadata.get("difficulty_level", 1)
                if isinstance(d, str):
                    try:
                        return int(d)
                    except (ValueError, TypeError):
                        return 1
                return d
            filtered = [r for r in filtered if get_diff(r) >= min_difficulty]

        if max_difficulty is not None:
            def get_diff(r):
                d = r.metadata.get("difficulty_level", 1)
                if isinstance(d, str):
                    try:
                        return int(d)
                    except (ValueError, TypeError):
                        return 1
                return d
            filtered = [r for r in filtered if get_diff(r) <= max_difficulty]

        if max_steps is not None:
            filtered = [
                r for r in filtered
                if r.trajectory is None or len(r.trajectory.steps) <= max_steps
            ]

        return filtered

    def filter_by_quality(
        self,
        results: list[RunResult],
        top_k: int | None = None,
        percentile: float | None = None,
    ) -> list[RunResult]:
        """Filter by reward quality, returning top-k or top percentile.

        Args:
            results: List of run results.
            top_k: Return top k highest-reward results.
            percentile: Return top percentile (0.0-1.0) of results.

        Returns:
            Filtered list sorted by reward (highest first).
        """
        exporter = TrajectoryExporter()
        scored = []
        for r in results:
            components = exporter._compute_reward_components(r)
            scored.append((components.get("total_reward", 0.0), r))

        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = [r for _, r in scored]

        if top_k is not None:
            return ranked[:top_k]

        if percentile is not None:
            count = max(1, int(len(ranked) * percentile))
            return ranked[:count]

        return ranked
