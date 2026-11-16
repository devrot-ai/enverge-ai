"""Parallel task execution runner.

Runs multiple tasks concurrently using ThreadPoolExecutor for faster
experiment execution.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from forge.agents.base import BaseAgent
from forge.agents.registry import AgentRegistry
from forge.core.schemas import (
    AgentConfig,
    RunConfig,
    RunResult,
    TaskSpec,
    WorldSpec,
)
from forge.runner.orchestrator import RunOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class ParallelRunResult:
    """Result of a parallel run across multiple tasks."""

    agent_type: str
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    passed: int = 0
    total_duration: float = 0.0
    results: list[RunResult] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.completed == 0:
            return 0.0
        return self.passed / self.completed

    @property
    def avg_duration(self) -> float:
        """Calculate average duration per completed task."""
        if self.completed == 0:
            return 0.0
        return self.total_duration / self.completed

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_type": self.agent_type,
            "total_tasks": self.total_tasks,
            "completed": self.completed,
            "failed": self.failed,
            "passed": self.passed,
            "pass_rate": round(self.pass_rate, 4),
            "avg_duration": round(self.avg_duration, 2),
            "total_duration": round(self.total_duration, 2),
            "errors": self.errors,
        }


def _run_single_task(
    task: TaskSpec,
    world: WorldSpec,
    agent: BaseAgent,
    artifacts_dir: str | None,
) -> tuple[TaskSpec, RunResult | None, dict[str, Any] | None]:
    """Run a single task. Worker function for ThreadPoolExecutor.

    Args:
        task: Task specification.
        world: World specification.
        agent: Agent instance.
        artifacts_dir: Directory for artifacts.

    Returns:
        Tuple of (task, result, error).
    """
    run_config = RunConfig(
        task_id=task.task_id,
        agent_id=agent.agent_id,
        timeout_seconds=300,
        max_steps=50,
    )

    try:
        orchestrator = RunOrchestrator(artifacts_dir=artifacts_dir)
        result = orchestrator.run(task, world, agent, run_config)
        return (task, result, None)
    except Exception as e:
        logger.error(f"Error running task {task.task_id}: {e}")
        return (task, None, {"task_id": task.task_id, "error": str(e)})


class ParallelRunner:
    """Run multiple tasks concurrently using threading.

    Uses ThreadPoolExecutor for parallel execution with configurable
    worker count.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        artifacts_dir: str | None = None,
        max_workers: int = 4,
    ):
        """Initialize the parallel runner.

        Args:
            registry: Agent registry for creating agents.
            artifacts_dir: Directory for storing run artifacts.
            max_workers: Maximum number of concurrent workers.
        """
        if registry is None:
            from forge.agents import registry as reg_module

            self.registry = reg_module.default_registry
        else:
            self.registry = registry
        self.artifacts_dir = artifacts_dir
        self.max_workers = max_workers

    def run(
        self,
        tasks: list[TaskSpec],
        worlds: list[WorldSpec],
        agent_type: str,
        agent_config: dict[str, Any] | None = None,
    ) -> ParallelRunResult:
        """Run multiple tasks in parallel.

        Args:
            tasks: List of task specifications.
            worlds: List of world specifications (one per task).
            agent_type: Agent type name.
            agent_config: Optional agent configuration overrides.

        Returns:
            ParallelRunResult with aggregate results.
        """
        result = ParallelRunResult(agent_type=agent_type, total_tasks=len(tasks))

        # Create agent config
        config_data = agent_config or {}
        agent_config_obj = AgentConfig(
            agent_type=agent_type,
            **{k: v for k, v in config_data.items() if k != "agent_type"},
        )

        logger.info(
            f"Running {len(tasks)} tasks in parallel with {self.max_workers} "
            f"workers using {agent_type}"
        )

        start_time = datetime.utcnow()

        # Create one agent per worker to avoid shared state
        agents = [
            self.registry.create(agent_config_obj)
            for _ in range(min(self.max_workers, len(tasks)))
        ]

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, (task, world) in enumerate(zip(tasks, worlds)):
                agent = agents[i % len(agents)]
                future = executor.submit(
                    _run_single_task, task, world, agent, self.artifacts_dir
                )
                futures[future] = task.task_id

            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    task, run_result, error = future.result()
                    if error:
                        result.failed += 1
                        result.errors.append(error)
                    elif run_result:
                        result.completed += 1
                        result.results.append(run_result)
                        result.total_duration += run_result.duration_seconds
                        if run_result.passed:
                            result.passed += 1
                        else:
                            result.failed += 1
                except Exception as e:
                    logger.error(f"Future failed for task {task_id}: {e}")
                    result.failed += 1
                    result.errors.append({"task_id": task_id, "error": str(e)})

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Parallel run complete: {result.completed}/{result.total_tasks} "
            f"completed, {result.passed} passed in {elapsed:.1f}s"
        )

        return result
