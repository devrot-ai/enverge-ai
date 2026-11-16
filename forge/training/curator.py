"""Example curation for training data quality.

Selects positive and negative examples from verified agent runs,
filtering by outcome and failure category. Only runs diagnosed as
`agent_failure` are used as negative examples per research methodology.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forge.core.schemas import RunResult, FailureCategory


@dataclass
class CuratedExample:
    """A curated training example from an agent run."""

    task_id: str
    agent_id: str
    is_positive: bool
    passed: bool
    reward: float = 0.0
    failure_category: FailureCategory | None = None
    trajectory_steps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "is_positive": self.is_positive,
            "passed": self.passed,
            "reward": self.reward,
            "failure_category": self.failure_category.value if self.failure_category else None,
            "trajectory_steps": self.trajectory_steps,
            "metadata": self.metadata,
        }


class ExampleCurator:
    """Curate positive and negative examples from agent runs.

    Selects examples based on run outcomes and failure categories.
    Only `agent_failure` diagnosed runs are used as negative examples.
    """

    def curate_positive(
        self,
        results: list[RunResult],
        min_reward: float | None = None,
    ) -> list[CuratedExample]:
        """Curate positive examples from passed runs.

        Args:
            results: List of run results.
            min_reward: Minimum reward threshold for inclusion.

        Returns:
            List of curated positive examples.
        """
        examples = []
        for result in results:
            if not result.passed:
                continue

            reward = 0.0
            if result.metadata:
                reward = result.metadata.get("reward", 0.0)

            if min_reward is not None and reward < min_reward:
                continue

            steps = 0
            if result.trajectory:
                steps = len(result.trajectory.steps)

            example = CuratedExample(
                task_id=result.task_id,
                agent_id=result.metadata.get("agent_id", "unknown"),
                is_positive=True,
                passed=True,
                reward=reward,
                trajectory_steps=steps,
                metadata=result.metadata or {},
            )
            examples.append(example)

        return examples

    def curate_negative(
        self,
        results: list[RunResult],
    ) -> list[CuratedExample]:
        """Curate negative examples from agent_failure diagnosed runs.

        Only runs diagnosed as `agent_failure` are included, per research
        methodology. Environment failures and other categories are excluded.

        Args:
            results: List of run results.

        Returns:
            List of curated negative examples.
        """
        examples = []
        for result in results:
            if result.passed:
                continue

            if (
                result.diagnosis
                and result.diagnosis.primary_category == FailureCategory.AGENT_FAILURE
            ):
                steps = 0
                if result.trajectory:
                    steps = len(result.trajectory.steps)

                example = CuratedExample(
                    task_id=result.task_id,
                    agent_id=result.metadata.get("agent_id", "unknown"),
                    is_positive=False,
                    passed=False,
                    failure_category=FailureCategory.AGENT_FAILURE,
                    trajectory_steps=steps,
                    metadata=result.metadata or {},
                )
                examples.append(example)

        return examples

    def curate_by_category(
        self,
        results: list[RunResult],
        category: FailureCategory,
    ) -> list[CuratedExample]:
        """Curate examples by a specific failure category.

        Args:
            results: List of run results.
            category: Failure category to filter by.

        Returns:
            List of curated examples with the specified failure category.
        """
        examples = []
        for result in results:
            if result.passed:
                continue

            if result.diagnosis and result.diagnosis.primary_category == category:
                steps = 0
                if result.trajectory:
                    steps = len(result.trajectory.steps)

                example = CuratedExample(
                    task_id=result.task_id,
                    agent_id=result.metadata.get("agent_id", "unknown"),
                    is_positive=False,
                    passed=False,
                    failure_category=category,
                    trajectory_steps=steps,
                    metadata=result.metadata or {},
                )
                examples.append(example)

        return examples

    def export_sft_format(
        self,
        examples: list[CuratedExample],
        output_path: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Export examples in Supervised Fine-Tuning (SFT) format.

        Each example is formatted as a conversation with system, user,
        and assistant messages.

        Args:
            examples: List of curated examples.
            output_path: Optional path to write JSONL file.

        Returns:
            List of SFT-formatted example dictionaries.
        """
        sft_examples = []
        for ex in examples:
            sft_example = {
                "messages": [
                    {
                        "role": "system",
                        "content": f"Task: {ex.task_id}. Agent: {ex.agent_id}.",
                    },
                    {
                        "role": "user",
                        "content": f"Task ID: {ex.task_id}",
                    },
                    {
                        "role": "assistant",
                        "content": (
                            "Success" if ex.is_positive else "Failure"
                        ),
                    },
                ],
                "metadata": {
                    "is_positive": ex.is_positive,
                    "reward": ex.reward,
                    "trajectory_steps": ex.trajectory_steps,
                },
            }
            sft_examples.append(sft_example)

        if output_path is not None:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                for example in sft_examples:
                    f.write(json.dumps(example, default=str) + "\n")

        return sft_examples

    def export_rl_format(
        self,
        examples: list[CuratedExample],
        output_path: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Export examples in Reinforcement Learning format.

        Each example includes state, action, and reward fields.

        Args:
            examples: List of curated examples.
            output_path: Optional path to write JSONL file.

        Returns:
            List of RL-formatted example dictionaries.
        """
        rl_examples = []
        for ex in examples:
            rl_example = {
                "state": {
                    "task_id": ex.task_id,
                    "agent_id": ex.agent_id,
                },
                "action": "execute_task",
                "reward": 1.0 if ex.is_positive else -1.0,
                "done": True,
                "metadata": ex.to_dict(),
            }
            rl_examples.append(rl_example)

        if output_path is not None:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                for example in rl_examples:
                    f.write(json.dumps(example, default=str) + "\n")

        return rl_examples
