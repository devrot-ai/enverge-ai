"""Experiment runner for end-to-end experiment execution.

Orchestrates task generation, agent execution, and result tracking
for experiments defined by ExperimentConfig presets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from forge.core.schemas import RunResult, RunStatus
from forge.experiments.manager import (
    ExperimentConfig,
    ExperimentManager,
    ExperimentRun,
)

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Result of running an experiment."""

    experiment_id: str
    name: str
    total_runs: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    success_rate: float = 0.0
    avg_duration: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    finished_at: str = ""


class ExperimentRunner:
    """Run experiments end-to-end.

    Generates or loads tasks, runs agents via RunOrchestrator,
    tracks results via ExperimentManager, and computes metrics.
    """

    def __init__(self, manager: ExperimentManager | None = None):
        """Initialize the runner.

        Args:
            manager: ExperimentManager instance. Creates a new one if not provided.
        """
        self.manager = manager or ExperimentManager()

    def run_experiment(
        self,
        config: ExperimentConfig,
        task_ids: list[str],
        agent_type: str = "mock",
        agent_factory: callable | None = None,
        orchestrator_run: callable | None = None,
    ) -> ExperimentResult:
        """Run a single experiment.

        Args:
            config: Experiment configuration.
            task_ids: List of task IDs to run.
            agent_type: Type of agent to use.
            agent_factory: Optional factory function that creates an agent.
            orchestrator_run: Optional function that runs an agent on a task
                and returns a RunResult. If not provided, creates mock results.

        Returns:
            ExperimentResult with metrics.
        """
        exp_id = self.manager.create_experiment(config)
        started_at = datetime.utcnow().isoformat()

        for task_id in task_ids:
            run_result = self._run_single_task(
                task_id=task_id,
                agent_type=agent_type,
                agent_factory=agent_factory,
                orchestrator_run=orchestrator_run,
            )

            run = ExperimentRun(
                run_id=f"run-{task_id}",
                task_id=task_id,
                result=run_result,
                started_at=started_at,
                finished_at=datetime.utcnow().isoformat(),
                duration_seconds=run_result.duration_seconds if run_result else 0.0,
            )
            self.manager.add_run(exp_id, run)

        self.manager.finish_experiment(exp_id)
        metrics = self.manager.compute_metrics(exp_id)

        return ExperimentResult(
            experiment_id=exp_id,
            name=config.name,
            total_runs=metrics.get("total_runs", 0),
            passed_runs=metrics.get("passed_runs", 0),
            failed_runs=metrics.get("failed_runs", 0),
            success_rate=metrics.get("success_rate", 0.0),
            avg_duration=metrics.get("avg_duration_seconds", 0.0),
            metrics=metrics,
            started_at=started_at,
            finished_at=datetime.utcnow().isoformat(),
        )

    def run_paired_experiment(
        self,
        config_a: ExperimentConfig,
        config_b: ExperimentConfig,
        task_ids: list[str],
        agent_factory: callable | None = None,
        orchestrator_run: callable | None = None,
    ) -> dict[str, Any]:
        """Run two experiments on the same tasks for comparison.

        Args:
            config_a: First experiment config.
            config_b: Second experiment config.
            task_ids: List of task IDs to run.
            agent_factory: Optional factory function that creates an agent.
            orchestrator_run: Optional function that runs an agent on a task.

        Returns:
            Comparison of the two experiments.
        """
        result_a = self.run_experiment(
            config=config_a,
            task_ids=task_ids,
            agent_type=config_a.agent_type,
            agent_factory=agent_factory,
            orchestrator_run=orchestrator_run,
        )

        result_b = self.run_experiment(
            config=config_b,
            task_ids=task_ids,
            agent_type=config_b.agent_type,
            agent_factory=agent_factory,
            orchestrator_run=orchestrator_run,
        )

        comparison = self.manager.compare(
            [result_a.experiment_id, result_b.experiment_id],
            metric="success_rate",
        )

        return {
            "experiment_a": {
                "id": result_a.experiment_id,
                "name": result_a.name,
                "success_rate": result_a.success_rate,
                "total_runs": result_a.total_runs,
            },
            "experiment_b": {
                "id": result_b.experiment_id,
                "name": result_b.name,
                "success_rate": result_b.success_rate,
                "total_runs": result_b.total_runs,
            },
            "comparison": comparison,
        }

    def _run_single_task(
        self,
        task_id: str,
        agent_type: str,
        agent_factory: callable | None = None,
        orchestrator_run: callable | None = None,
    ) -> RunResult | None:
        """Run a single task, using the orchestrator or creating a mock result.

        Args:
            task_id: The task ID to run.
            agent_type: Type of agent.
            agent_factory: Optional agent factory.
            orchestrator_run: Optional orchestrator run function.

        Returns:
            RunResult or None if execution fails.
        """
        if orchestrator_run is not None:
            try:
                return orchestrator_run(task_id, agent_type)
            except Exception as e:
                logger.error(f"Error running task {task_id}: {e}")
                return self._create_error_result(task_id, str(e))
        else:
            # Create a mock result for testing
            return self._create_mock_result(task_id, agent_type)

    def _create_mock_result(self, task_id: str, agent_type: str) -> RunResult:
        """Create a mock RunResult for testing.

        Args:
            task_id: The task ID.
            agent_type: The agent type.

        Returns:
            A mock RunResult.
        """
        from forge.core.schemas import Trajectory, TrajectoryStep

        traj = Trajectory(run_id=f"run-{task_id}", task_id=task_id, agent_id=agent_type)
        traj.add_step(
            TrajectoryStep(
                step_index=0,
                action="mock_execute",
                tool_name="mock_tool",
                tool_result="success",
                duration_seconds=0.1,
            )
        )

        result = RunResult(
            run_id=f"run-{task_id}",
            task_id=task_id,
            agent_id=agent_type,
            status=RunStatus.COMPLETED,
        )
        result.passed = True
        result.step_count = 1
        result.duration_seconds = 0.1
        result.trajectory = traj
        result.metadata = {
            "agent_id": agent_type,
            "task_id": task_id,
        }
        return result

    def _create_error_result(self, task_id: str, error: str) -> RunResult:
        """Create an error RunResult.

        Args:
            task_id: The task ID.
            error: Error message.

        Returns:
            A RunResult with error status.
        """
        result = RunResult(
            run_id=f"run-{task_id}",
            task_id=task_id,
            agent_id="unknown",
            status=RunStatus.FAILED,
        )
        result.passed = False
        result.step_count = 0
        result.duration_seconds = 0.0
        result.error = error
        result.metadata = {"task_id": task_id}
        return result
