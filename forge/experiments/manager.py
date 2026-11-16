"""Experiment management for ForgeLab.

Supports creating, running, and comparing experiments that test different
curriculum strategies, validation approaches, and task selection methods.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from forge.core.schemas import CurriculumStrategy, RunResult

logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    uid = uuid4().hex[:12]
    return f"{prefix}{uid}" if prefix else uid


# ---------------------------------------------------------------------------
# Experiment Configuration
# ---------------------------------------------------------------------------


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment.

    Attributes:
        experiment_id: Unique identifier.
        name: Human-readable name.
        description: What this experiment tests.
        hypothesis: The research hypothesis being tested.
        agent_type: Type of agent (e.g. "mock", "openai_compatible").
        agent_model: Model identifier for LLM agents.
        curriculum_strategy: Task selection strategy.
        validation_enabled: Whether independent validation is used.
        task_source: Where tasks come from ("seeded", "generated", "heldout").
        max_runs: Maximum number of runs in this experiment.
        seed: Random seed for reproducibility.
        metadata: Additional configuration.
    """

    name: str
    hypothesis: str
    experiment_id: str | None = None
    description: str = ""
    agent_type: str = "mock"
    agent_model: str | None = None
    curriculum_strategy: CurriculumStrategy = CurriculumStrategy.STATIC
    validation_enabled: bool = True
    task_source: str = "seeded"
    max_runs: int = 20
    seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.experiment_id is None:
            self.experiment_id = generate_id("exp-")
        if isinstance(self.curriculum_strategy, str):
            self.curriculum_strategy = CurriculumStrategy(self.curriculum_strategy)


# ---------------------------------------------------------------------------
# Experiment Run Record
# ---------------------------------------------------------------------------


@dataclass
class ExperimentRun:
    """Record of a single run within an experiment.

    Attributes:
        run_id: The run identifier.
        task_id: The task attempted.
        result: The run result.
        started_at: When the run started.
        finished_at: When the run finished.
        duration_seconds: Wall-clock duration.
    """

    run_id: str
    task_id: str
    result: RunResult | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Experiment Manager
# ---------------------------------------------------------------------------


class ExperimentManager:
    """Manages the lifecycle of experiments.

    Creates experiments, tracks runs, computes metrics, and compares
    results between experiments.

    Usage:
        manager = ExperimentManager()
        exp_id = manager.create_experiment(config)
        manager.add_run(exp_id, run_result)
        metrics = manager.compute_metrics(exp_id)
        comparison = manager.compare([exp_id_1, exp_id_2])
    """

    def __init__(self):
        self._experiments: dict[str, ExperimentConfig] = {}
        self._runs: dict[str, list[ExperimentRun]] = {}
        self._started_at: dict[str, str] = {}
        self._finished_at: dict[str, str | None] = {}

    def create_experiment(self, config: ExperimentConfig) -> str:
        """Create a new experiment.

        Args:
            config: Experiment configuration.

        Returns:
            The experiment ID.
        """
        self._experiments[config.experiment_id] = config
        self._runs[config.experiment_id] = []
        self._started_at[config.experiment_id] = datetime.utcnow().isoformat()
        self._finished_at[config.experiment_id] = None
        logger.info(
            f"Created experiment {config.experiment_id}: {config.name} "
            f"(strategy={config.curriculum_strategy.value})"
        )
        return config.experiment_id

    def add_run(self, experiment_id: str, run: ExperimentRun) -> None:
        """Add a run result to an experiment.

        Args:
            experiment_id: The experiment to add to.
            run: The run record.
        """
        if experiment_id not in self._runs:
            raise ValueError(f"Experiment {experiment_id} not found")
        self._runs[experiment_id].append(run)
        logger.info(
            f"Added run {run.run_id} to experiment {experiment_id} " f"({len(self._runs[experiment_id])} runs total)"
        )

    def finish_experiment(self, experiment_id: str) -> None:
        """Mark an experiment as finished.

        Args:
            experiment_id: The experiment to finish.
        """
        if experiment_id not in self._experiments:
            raise ValueError(f"Experiment {experiment_id} not found")
        self._finished_at[experiment_id] = datetime.utcnow().isoformat()
        logger.info(f"Finished experiment {experiment_id}")

    def get_experiment(self, experiment_id: str) -> ExperimentConfig | None:
        """Get an experiment's configuration.

        Args:
            experiment_id: The experiment ID.

        Returns:
            The experiment config or None.
        """
        return self._experiments.get(experiment_id)

    def get_runs(self, experiment_id: str) -> list[ExperimentRun]:
        """Get all runs for an experiment.

        Args:
            experiment_id: The experiment ID.

        Returns:
            List of run records.
        """
        return self._runs.get(experiment_id, [])

    def compute_metrics(self, experiment_id: str) -> dict[str, Any]:
        """Compute aggregate metrics for an experiment.

        Args:
            experiment_id: The experiment ID.

        Returns:
            Dictionary of metrics.
        """
        runs = self.get_runs(experiment_id)
        config = self.get_experiment(experiment_id)

        if not runs:
            return {
                "experiment_id": experiment_id,
                "name": config.name if config else "unknown",
                "total_runs": 0,
                "message": "No runs yet",
            }

        total = len(runs)
        completed = sum(1 for r in runs if r.result and self._status_value(r.result.status) == "completed")
        passed = sum(1 for r in runs if r.result and r.result.passed)
        failed = total - completed

        # Failure attribution breakdown
        failure_counts: dict[str, int] = {}
        for r in runs:
            if r.result and r.result.diagnosis:
                cat = r.result.diagnosis.primary_category.value
                failure_counts[cat] = failure_counts.get(cat, 0) + 1

        # Duration stats
        durations = [r.duration_seconds for r in runs if r.duration_seconds > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Step count stats
        step_counts = [r.result.step_count for r in runs if r.result and r.result.step_count > 0]
        avg_steps = sum(step_counts) / len(step_counts) if step_counts else 0

        return {
            "experiment_id": experiment_id,
            "name": config.name if config else "unknown",
            "hypothesis": config.hypothesis if config else "",
            "strategy": config.curriculum_strategy.value if config else "unknown",
            "total_runs": total,
            "completed_runs": completed,
            "passed_runs": passed,
            "failed_runs": failed,
            "success_rate": passed / total if total > 0 else 0.0,
            "completion_rate": completed / total if total > 0 else 0.0,
            "failure_breakdown": failure_counts,
            "avg_duration_seconds": round(avg_duration, 2),
            "avg_steps": round(avg_steps, 1),
            "validation_enabled": config.validation_enabled if config else True,
        }

    def compare(self, experiment_ids: list[str], metric: str = "success_rate") -> dict[str, Any]:
        """Compare multiple experiments on a given metric.

        Args:
            experiment_ids: List of experiment IDs to compare.
            metric: Which metric to compare (default: "success_rate").

        Returns:
            Comparison results with rankings.
        """
        comparisons = []
        for exp_id in experiment_ids:
            metrics = self.compute_metrics(exp_id)
            comparisons.append(
                {
                    "experiment_id": exp_id,
                    "name": metrics.get("name", "unknown"),
                    "strategy": metrics.get("strategy", "unknown"),
                    "metric_value": metrics.get(metric, 0.0),
                    "total_runs": metrics.get("total_runs", 0),
                    "all_metrics": metrics,
                }
            )

        # Sort by metric value descending
        comparisons.sort(key=lambda x: x["metric_value"], reverse=True)

        return {
            "metric": metric,
            "comparison": comparisons,
            "best": comparisons[0]["name"] if comparisons else None,
            "worst": comparisons[-1]["name"] if comparisons else None,
        }

    def list_experiments(self) -> list[dict[str, Any]]:
        """List all experiments with summary info.

        Returns:
            List of experiment summaries.
        """
        result = []
        for exp_id, config in self._experiments.items():
            runs = self.get_runs(exp_id)
            result.append(
                {
                    "experiment_id": exp_id,
                    "name": config.name,
                    "strategy": config.curriculum_strategy.value,
                    "run_count": len(runs),
                    "started_at": self._started_at.get(exp_id),
                    "finished_at": self._finished_at.get(exp_id),
                }
            )
        return result

    def export_experiment(self, experiment_id: str, path: str) -> None:
        """Export an experiment's data to a JSON file.

        Args:
            experiment_id: The experiment to export.
            path: File path to write to.
        """
        config = self.get_experiment(experiment_id)
        if not config:
            raise ValueError(f"Experiment {experiment_id} not found")

        runs = self.get_runs(experiment_id)
        metrics = self.compute_metrics(experiment_id)

        data = {
            "config": {
                "experiment_id": config.experiment_id,
                "name": config.name,
                "description": config.description,
                "hypothesis": config.hypothesis,
                "agent_type": config.agent_type,
                "curriculum_strategy": config.curriculum_strategy.value,
                "validation_enabled": config.validation_enabled,
                "max_runs": config.max_runs,
                "seed": config.seed,
            },
            "metrics": metrics,
            "runs": [
                {
                    "run_id": r.run_id,
                    "task_id": r.task_id,
                    "duration_seconds": r.duration_seconds,
                    "result": r.result.to_dict() if r.result else None,
                }
                for r in runs
            ],
            "started_at": self._started_at.get(experiment_id),
            "finished_at": self._finished_at.get(experiment_id),
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Exported experiment {experiment_id} to {path}")

    @staticmethod
    def _status_value(status) -> str:
        """Extract string value from RunStatus enum or string."""
        if hasattr(status, "value"):
            return status.value
        return str(status)


# ---------------------------------------------------------------------------
# Preset Experiments
# ---------------------------------------------------------------------------


def create_experiment_a() -> ExperimentConfig:
    """Experiment A: Fixed curriculum vs adaptive curriculum.

    Question: Does adaptive task selection improve performance on a
    fixed held-out benchmark?
    """
    return ExperimentConfig(
        name="Static vs Adaptive Curriculum",
        hypothesis="Adaptive task selection produces better agent performance on held-out tasks than static curriculum",
        curriculum_strategy=CurriculumStrategy.ADAPTIVE,
        validation_enabled=True,
        task_source="seeded",
        max_runs=20,
    )


def create_experiment_b() -> ExperimentConfig:
    """Experiment B: Unvalidated vs validated task generation.

    Question: How many misleading failures are caused by broken worlds?
    """
    return ExperimentConfig(
        name="Unvalidated vs Validated Tasks",
        hypothesis="Independent environment validation reduces misleading agent-failure signals",
        curriculum_strategy=CurriculumStrategy.RANDOM,
        validation_enabled=True,
        task_source="generated",
        max_runs=20,
    )


def create_experiment_c() -> ExperimentConfig:
    """Experiment C: Random vs failure-targeted task selection.

    Question: Does targeted practice improve transfer to unseen problems?
    """
    return ExperimentConfig(
        name="Random vs Targeted Task Selection",
        hypothesis="Targeted tasks improve agent capability on related unseen problems",
        curriculum_strategy=CurriculumStrategy.ADAPTIVE,
        validation_enabled=True,
        task_source="seeded",
        max_runs=20,
    )


def create_experiment_d() -> ExperimentConfig:
    """Experiment D: Generator-only vs independent verification.

    Question: How much does independent verification improve training-data quality?
    """
    return ExperimentConfig(
        name="Generator-only vs Independent Verification",
        hypothesis="Independent verification improves training-data quality over generator-only validation",
        curriculum_strategy=CurriculumStrategy.STATIC,
        validation_enabled=True,
        task_source="seeded",
        max_runs=20,
    )


def create_experiment_ablation_tools() -> ExperimentConfig:
    """Experiment E: Tool ablation study.

    Question: Which tools contribute most to agent performance?
    Run agent with progressively fewer tools to measure tool importance.
    """
    return ExperimentConfig(
        name="Tool Ablation Study",
        hypothesis="Removing diagnostic tools (read_file, search_code) reduces agent performance more than removing utility tools",
        curriculum_strategy=CurriculumStrategy.STATIC,
        validation_enabled=True,
        task_source="seeded",
        max_runs=20,
        metadata={
            "ablation_type": "tools",
            "tool_sets": [
                ["read_file", "write_file", "search_code", "run_tests", "list_files"],
                ["read_file", "write_file", "run_tests", "list_files"],
                ["read_file", "write_file", "run_tests"],
                ["read_file", "write_file"],
            ],
        },
    )


def create_experiment_difficulty_scaling() -> ExperimentConfig:
    """Experiment F: Difficulty scaling analysis.

    Question: How does agent performance scale with task difficulty?
    Measure agent performance across difficulty levels 1-5.
    """
    return ExperimentConfig(
        name="Difficulty Scaling Analysis",
        hypothesis="Agent performance degrades non-linearly with difficulty, with a sharp drop at difficulty 4+",
        curriculum_strategy=CurriculumStrategy.STATIC,
        validation_enabled=True,
        task_source="seeded",
        max_runs=50,
        metadata={
            "scaling_type": "difficulty",
            "difficulty_levels": [1, 2, 3, 4, 5],
            "runs_per_level": 10,
        },
    )


def create_experiment_cross_template() -> ExperimentConfig:
    """Experiment G: Cross-template generalization.

    Question: How well does an agent generalize across different application templates?
    Run the same agent across all templates to measure generalization ability.
    """
    return ExperimentConfig(
        name="Cross-Template Generalization",
        hypothesis="Agents trained on one template show limited transfer to structurally different templates",
        curriculum_strategy=CurriculumStrategy.ADAPTIVE,
        validation_enabled=True,
        task_source="generated",
        max_runs=40,
        metadata={
            "generalization_type": "cross_template",
            "templates": [
                "task_manager_api",
                "data_pipeline",
                "flask_app",
                "express_api",
                "django_app",
            ],
            "runs_per_template": 8,
        },
    )
