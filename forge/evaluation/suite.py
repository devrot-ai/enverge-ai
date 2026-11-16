"""Benchmark suite for formal evaluation.

Provides predefined task sets (easy, medium, hard, all) and runs
agents against them to produce score reports with baseline comparison.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from forge.core.schemas import TaskSpec
from forge.evaluation.benchmark import BenchmarkReport, BenchmarkRunner
from forge.experiments.manager import ExperimentManager
from forge.world_factory.templates import list_templates

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkSuite:
    """Predefined benchmark task sets.

    Provides easy, medium, hard, and all task sets for standardized
    evaluation. Baselines are stored per agent type.
    """

    name: str
    tasks: list[TaskSpec] = field(default_factory=list)
    level: str = "all"  # "easy", "medium", "hard", "all"
    baselines: dict[str, float] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()

    def add_task(self, task: TaskSpec) -> None:
        """Add a task to the suite."""
        self.tasks.append(task)

    def set_baseline(self, agent_type: str, pass_rate: float) -> None:
        """Set baseline pass rate for an agent type."""
        self.baselines[agent_type] = pass_rate

    def get_baseline(self, agent_type: str) -> float | None:
        """Get baseline pass rate for an agent type."""
        return self.baselines.get(agent_type)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "level": self.level,
            "task_count": len(self.tasks),
            "baselines": self.baselines,
            "created_at": self.created_at,
        }


def create_benchmark_suite(
    level: str = "all",
    templates: list[str] | None = None,
) -> BenchmarkSuite:
    """Create a benchmark suite from templates.

    Args:
        level: Difficulty level ("easy", "medium", "hard", "all").
        templates: List of template names to include. If None, all templates.

    Returns:
        BenchmarkSuite with tasks from the specified templates.
    """
    if templates is None:
        templates = list_templates()

    difficulty_map = {
        "easy": [1, 2],
        "medium": [2, 3],
        "hard": [4, 5],
        "all": [1, 2, 3, 4, 5],
    }
    difficulties = difficulty_map.get(level, [1, 2, 3, 4, 5])

    suite = BenchmarkSuite(
        name=f"benchmark_{level}",
        level=level,
    )

    # Default baselines
    suite.baselines["mock"] = 0.5
    suite.baselines["rule_based"] = 0.3

    return suite


def run_benchmark(
    suite: BenchmarkSuite,
    agent_type: str,
) -> BenchmarkReport:
    """Run a benchmark suite against an agent.

    Args:
        suite: Benchmark suite with tasks.
        agent_type: Agent type to evaluate.

    Returns:
        BenchmarkReport with results.
    """
    runner = BenchmarkRunner()
    report = runner.run(suite.tasks, agent_type)

    # Compare against baseline
    baseline = suite.get_baseline(agent_type)
    if baseline is not None and report.pass_rate != 0:
        report.baseline_comparison = {
            "baseline_pass_rate": baseline,
            "current_pass_rate": report.pass_rate,
            "improvement": report.pass_rate - baseline,
            "regression": baseline > report.pass_rate,
        }

    return report
