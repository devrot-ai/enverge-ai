"""Multi-agent comparison runner.

Runs multiple agents on the same set of tasks and produces a side-by-side
comparison report with pass rates, timing, and failure categories.
"""

from __future__ import annotations

import logging
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
class AgentComparison:
    """Comparison result for a single agent across multiple tasks."""

    agent_type: str
    agent_id: str
    total_tasks: int = 0
    passed: int = 0
    failed: int = 0
    timed_out: int = 0
    total_duration: float = 0.0
    results: list[RunResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.passed / self.total_tasks

    @property
    def avg_duration(self) -> float:
        """Calculate average duration per task."""
        if self.total_tasks == 0:
            return 0.0
        return self.total_duration / self.total_tasks

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "total_tasks": self.total_tasks,
            "passed": self.passed,
            "failed": self.failed,
            "timed_out": self.timed_out,
            "pass_rate": round(self.pass_rate, 4),
            "avg_duration": round(self.avg_duration, 2),
            "total_duration": round(self.total_duration, 2),
        }


@dataclass
class MultiAgentReport:
    """Full comparison report across all agents and tasks."""

    comparisons: list[AgentComparison] = field(default_factory=list)
    task_count: int = 0
    completed_at: str = ""

    def add_comparison(self, comparison: AgentComparison) -> None:
        """Add an agent comparison result."""
        self.comparisons.append(comparison)

    def generate_summary(self) -> dict[str, Any]:
        """Generate a summary of all comparisons."""
        return {
            "task_count": self.task_count,
            "agent_count": len(self.comparisons),
            "completed_at": self.completed_at,
            "comparisons": [c.to_dict() for c in self.comparisons],
        }

    def to_markdown(self) -> str:
        """Generate a Markdown table comparison."""
        lines = ["# Multi-Agent Comparison Report", ""]
        lines.append(f"**Tasks:** {self.task_count} | **Agents:** {len(self.comparisons)}")
        lines.append("")
        lines.append("| Agent | Tasks | Passed | Failed | Pass Rate | Avg Duration |")
        lines.append("|-------|-------|--------|--------|-----------|--------------|")
        for comp in self.comparisons:
            lines.append(
                f"| {comp.agent_type} | {comp.total_tasks} | {comp.passed} "
                f"| {comp.failed} | {comp.pass_rate:.1%} | {comp.avg_duration:.1f}s |"
            )
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.generate_summary()


class MultiAgentRunner:
    """Run multiple agents on the same tasks and compare results.

    Each agent runs all tasks sequentially. Results are collected and
    compared side by side.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        artifacts_dir: str | None = None,
    ):
        """Initialize the multi-agent runner.

        Args:
            registry: Agent registry for creating agents. If None, a new
                registry is created with default agents.
            artifacts_dir: Directory for storing run artifacts.
        """
        if registry is None:
            self.registry = AgentRegistry()
            # Auto-register default agents
            from forge.agents import registry as reg_module

            self.registry = reg_module.default_registry
        else:
            self.registry = registry
        self.artifacts_dir = artifacts_dir

    def run(
        self,
        tasks: list[TaskSpec],
        worlds: list[WorldSpec],
        agent_types: list[str],
        agent_configs: dict[str, dict[str, Any]] | None = None,
    ) -> MultiAgentReport:
        """Run multiple agents on the same tasks.

        Args:
            tasks: List of task specifications.
            worlds: List of world specifications (one per task).
            agent_types: List of agent type names to compare.
            agent_configs: Optional per-agent configuration overrides.

        Returns:
            MultiAgentReport with comparison results.
        """
        report = MultiAgentReport(
            task_count=len(tasks),
            completed_at=datetime.utcnow().isoformat(),
        )

        agent_configs = agent_configs or {}

        for agent_type in agent_types:
            logger.info(f"Running agent type: {agent_type}")
            comparison = AgentComparison(
                agent_type=agent_type,
                agent_id=f"{agent_type}-comparison",
            )

            # Create agent config
            config_data = agent_configs.get(agent_type, {})
            agent_config = AgentConfig(
                agent_type=agent_type,
                **{k: v for k, v in config_data.items() if k != "agent_type"},
            )

            agent = self.registry.create(agent_config)
            orchestrator = RunOrchestrator(
                artifacts_dir=self.artifacts_dir,
            )

            for i, task in enumerate(tasks):
                world = worlds[i] if i < len(worlds) else None
                if world is None:
                    logger.warning(f"No world for task {task.task_id}, skipping")
                    continue

                run_config = RunConfig(
                    task_id=task.task_id,
                    agent_id=agent.agent_id,
                    timeout_seconds=300,
                    max_steps=50,
                )

                try:
                    result = orchestrator.run(task, world, agent, run_config)
                    comparison.results.append(result)
                    comparison.total_tasks += 1
                    comparison.total_duration += result.duration_seconds

                    if result.passed:
                        comparison.passed += 1
                    elif result.status.value == "timed_out":
                        comparison.timed_out += 1
                    else:
                        comparison.failed += 1

                except Exception as e:
                    logger.error(f"Error running {agent_type} on {task.task_id}: {e}")
                    comparison.failed += 1
                    comparison.total_tasks += 1

            report.add_comparison(comparison)
            logger.info(
                f"Agent {agent_type}: {comparison.passed}/{comparison.total_tasks} "
                f"passed ({comparison.pass_rate:.1%})"
            )

        return report
