"""Normalized trajectory export for training data.

Converts internal ForgeLab trajectory format to a normalized JSONL format
suitable for training data pipelines. Each trajectory includes the full
agent interaction history, task context, and outcome.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.core.schemas import RunResult, TaskSpec, Trajectory, TrajectoryStep

logger = logging.getLogger(__name__)

# Schema version for normalized trajectories
SCHEMA_VERSION = "1.0.0"


@dataclass
class NormalizedTrajectory:
    """Normalized trajectory for training data export.

    This format is independent of ForgeLab's internal schema and designed
    for consumption by external training pipelines.
    """

    run_id: str
    task_id: str
    agent_type: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = ""
    passed: bool = False
    duration_seconds: float = 0.0
    verification_passed: bool = False
    failure_category: str = ""
    task_category: str = ""
    difficulty_level: int = 1
    template_name: str = ""
    mutation_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class TrajectoryNormalizer:
    """Convert internal ForgeLab trajectories to normalized format.

    Transforms Trajectory objects along with run results and task specs
    into the normalized format suitable for training data export.
    """

    def __init__(self):
        """Initialize the normalizer."""
        pass

    def normalize(
        self,
        trajectory: Trajectory,
        run_result: RunResult,
        task_spec: TaskSpec,
    ) -> NormalizedTrajectory:
        """Normalize a single trajectory.

        Args:
            trajectory: Internal trajectory object.
            run_result: Run result with pass/fail status.
            task_spec: Task specification with metadata.

        Returns:
            NormalizedTrajectory in standard format.
        """
        # Convert trajectory steps to normalized format
        steps = []
        for step in trajectory.steps:
            normalized_step = self._normalize_step(step)
            steps.append(normalized_step)

        # Extract task metadata
        task_category = ""
        difficulty_level = 1
        template_name = ""
        mutation_name = ""

        if hasattr(task_spec, "category"):
            task_category = task_spec.category.value if task_spec.category else ""
        if hasattr(task_spec, "difficulty_level"):
            difficulty_level = task_spec.difficulty_level or 1
        if hasattr(task_spec, "metadata") and task_spec.metadata:
            template_name = task_spec.metadata.get("template_name", "")
            mutation_name = task_spec.metadata.get("mutation_name", "")

        # Extract failure category from diagnosis
        failure_category = ""
        if hasattr(run_result, "diagnosis") and run_result.diagnosis:
            failure_category = (
                run_result.diagnosis.primary_category.value
                if hasattr(run_result.diagnosis.primary_category, "value")
                else str(run_result.diagnosis.primary_category)
            )

        return NormalizedTrajectory(
            run_id=run_result.run_id,
            task_id=task_spec.task_id,
            agent_type=run_result.agent_id,
            steps=steps,
            outcome=run_result.status.value if hasattr(run_result.status, "value") else str(run_result.status),
            passed=run_result.passed,
            duration_seconds=run_result.duration_seconds,
            verification_passed=(
                run_result.verification.passed if run_result.verification else False
            ),
            failure_category=failure_category,
            task_category=task_category,
            difficulty_level=difficulty_level,
            template_name=template_name,
            mutation_name=mutation_name,
            metadata={
                "created_at": datetime.utcnow().isoformat(),
                "forge_lab_version": "0.5",
            },
        )

    def _normalize_step(self, step: TrajectoryStep) -> dict[str, Any]:
        """Normalize a single trajectory step.

        Args:
            step: Internal trajectory step.

        Returns:
            Dictionary with normalized step data.
        """
        normalized = {
            "step_number": step.step_index,
            "tool_name": step.tool_name or "",
            "tool_input": step.tool_arguments or {},
            "tool_output": step.tool_result or "",
            "observation": step.observation,
            "action": step.action,
            "duration_seconds": step.duration_seconds,
        }

        # Add optional fields
        if step.error:
            normalized["error"] = step.error
        if step.metadata:
            normalized["metadata"] = step.metadata

        return normalized

    def normalize_batch(
        self,
        trajectories: list[Trajectory],
        run_results: list[RunResult],
        task_specs: list[TaskSpec],
    ) -> list[NormalizedTrajectory]:
        """Normalize a batch of trajectories.

        Args:
            trajectories: List of internal trajectories.
            run_results: List of run results.
            task_specs: List of task specifications.

        Returns:
            List of normalized trajectories.
        """
        normalized = []
        for i, (trajectory, run_result, task_spec) in enumerate(
            zip(trajectories, run_results, task_specs)
        ):
            try:
                norm = self.normalize(trajectory, run_result, task_spec)
                normalized.append(norm)
            except Exception as e:
                logger.error(f"Error normalizing trajectory {i}: {e}")
        return normalized

    def export_jsonl(
        self,
        trajectories: list[NormalizedTrajectory],
        output_path: str | Path,
    ) -> int:
        """Export normalized trajectories as JSONL.

        Args:
            trajectories: List of normalized trajectories.
            output_path: Path to output JSONL file.

        Returns:
            Number of trajectories written.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for traj in trajectories:
                f.write(json.dumps(traj.to_dict()) + "\n")
                count += 1

        logger.info(f"Exported {count} trajectories to {output_path}")
        return count
