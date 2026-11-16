"""Benchmark runner for held-out evaluation.

Runs a set of tasks against an agent and produces a score report
with pass rate, capability breakdown, and timing information.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.agents.base import BaseAgent
from forge.core.schemas import (
    RunConfig,
    TaskSpec,
)
from forge.evaluation.verifier import Verifier
from forge.runner.orchestrator import RunOrchestrator


@dataclass
class BenchmarkResult:
    """Result of a single task in a benchmark run."""

    task_id: str
    task_name: str
    template: str
    mutation: str
    difficulty: int
    category: str
    passed: bool
    duration: float
    failure_category: str | None = None
    trajectory_steps: int = 0


@dataclass
class BenchmarkReport:
    """Complete benchmark report with summary statistics."""

    benchmark_id: str
    agent_type: str
    timestamp: str
    total_tasks: int
    passed_tasks: int
    failed_tasks: int
    pass_rate: float
    avg_duration: float
    results: list[BenchmarkResult] = field(default_factory=list)
    capability_breakdown: dict[str, dict[str, int]] = field(default_factory=dict)
    template_breakdown: dict[str, dict[str, int]] = field(default_factory=dict)
    difficulty_breakdown: dict[int, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "benchmark_id": self.benchmark_id,
            "agent_type": self.agent_type,
            "timestamp": self.timestamp,
            "total_tasks": self.total_tasks,
            "passed_tasks": self.passed_tasks,
            "failed_tasks": self.failed_tasks,
            "pass_rate": self.pass_rate,
            "avg_duration": round(self.avg_duration, 2),
            "capability_breakdown": self.capability_breakdown,
            "template_breakdown": self.template_breakdown,
            "difficulty_breakdown": {str(k): v for k, v in self.difficulty_breakdown.items()},
            "results": [
                {
                    "task_id": r.task_id,
                    "task_name": r.task_name,
                    "template": r.template,
                    "mutation": r.mutation,
                    "difficulty": r.difficulty,
                    "category": r.category,
                    "passed": r.passed,
                    "duration": round(r.duration, 2),
                    "failure_category": r.failure_category,
                    "trajectory_steps": r.trajectory_steps,
                }
                for r in self.results
            ],
        }

    def to_markdown(self) -> str:
        """Generate a Markdown table summary of the benchmark."""
        lines = [
            f"# Benchmark Report: {self.benchmark_id}",
            "",
            f"- **Agent**: {self.agent_type}",
            f"- **Date**: {self.timestamp}",
            f"- **Total Tasks**: {self.total_tasks}",
            f"- **Passed**: {self.passed_tasks}",
            f"- **Failed**: {self.failed_tasks}",
            f"- **Pass Rate**: {self.pass_rate:.1%}",
            f"- **Avg Duration**: {self.avg_duration:.2f}s",
            "",
            "## Results",
            "",
            "| Task | Template | Mutation | Difficulty | Passed | Duration |",
            "|------|----------|----------|------------|--------|----------|",
        ]

        for r in self.results:
            status = "✓" if r.passed else "✗"
            lines.append(
                f"| {r.task_id} | {r.template} | {r.mutation} | {r.difficulty} | {status} | {r.duration:.2f}s |"
            )

        if self.capability_breakdown:
            lines.append("")
            lines.append("## Capability Breakdown")
            lines.append("")
            lines.append("| Capability | Passed | Failed | Rate |")
            lines.append("|------------|--------|--------|------|")
            for cap, counts in sorted(self.capability_breakdown.items()):
                total = counts.get("passed", 0) + counts.get("failed", 0)
                rate = counts.get("passed", 0) / total if total > 0 else 0
                lines.append(f"| {cap} | {counts.get('passed', 0)} | {counts.get('failed', 0)} | {rate:.1%} |")

        return "\n".join(lines)


class BenchmarkRunner:
    """Runs a set of tasks against an agent and produces a benchmark report."""

    def __init__(
        self,
        agent: BaseAgent,
        orchestrator: RunOrchestrator | None = None,
        verifier: Verifier | None = None,
    ):
        self.agent = agent
        self.orchestrator = orchestrator or RunOrchestrator()
        self.verifier = verifier or Verifier()

    def run(
        self,
        tasks: list[TaskSpec],
        workspace_base: Path,
        run_config: RunConfig | None = None,
    ) -> BenchmarkReport:
        """Run all tasks against the agent and produce a report.

        Args:
            tasks: List of task specifications to run.
            workspace_base: Base directory for workspaces.
            run_config: Optional run configuration override.

        Returns:
            BenchmarkReport with results and statistics.
        """
        if run_config is None:
            run_config = RunConfig(
                task_id="benchmark",
                agent_id=self.agent.agent_type,
                max_steps=50,
                timeout_seconds=300,
            )

        benchmark_id = f"bench-{self.agent.agent_type}-{int(time.time())}"
        results: list[BenchmarkResult] = []
        total_duration = 0.0

        for task in tasks:
            task_start = time.time()
            workspace = workspace_base / task.task_id

            try:
                # Run the agent on the task
                trajectory = self.agent.execute(task, workspace, run_config)

                # Verify the result
                verification = self.verifier.verify(workspace, task)

                duration = time.time() - task_start
                total_duration += duration

                result = BenchmarkResult(
                    task_id=task.task_id,
                    task_name=task.description[:50] if task.description else "",
                    template=task.metadata.get("template", "unknown"),
                    mutation=task.metadata.get("mutation", "unknown"),
                    difficulty=task.difficulty_level,
                    category=task.category.value if task.category else "unknown",
                    passed=verification.passed,
                    duration=duration,
                    failure_category=(verification.failure_category.value if verification.failure_category else None),
                    trajectory_steps=len(trajectory.steps),
                )
                results.append(result)

            except Exception:
                duration = time.time() - task_start
                total_duration += duration

                results.append(
                    BenchmarkResult(
                        task_id=task.task_id,
                        task_name=task.description[:50] if task.description else "",
                        template=task.metadata.get("template", "unknown"),
                        mutation=task.metadata.get("mutation", "unknown"),
                        difficulty=task.difficulty_level,
                        category=task.category.value if task.category else "unknown",
                        passed=False,
                        duration=duration,
                        failure_category="environment_failure",
                        trajectory_steps=0,
                    )
                )

        # Calculate breakdowns
        capability_breakdown: dict[str, dict[str, int]] = {}
        template_breakdown: dict[str, dict[str, int]] = {}
        difficulty_breakdown: dict[int, dict[str, int]] = {}

        for r in results:
            # Capability breakdown
            cap = r.category
            if cap not in capability_breakdown:
                capability_breakdown[cap] = {"passed": 0, "failed": 0}
            if r.passed:
                capability_breakdown[cap]["passed"] += 1
            else:
                capability_breakdown[cap]["failed"] += 1

            # Template breakdown
            tpl = r.template
            if tpl not in template_breakdown:
                template_breakdown[tpl] = {"passed": 0, "failed": 0}
            if r.passed:
                template_breakdown[tpl]["passed"] += 1
            else:
                template_breakdown[tpl]["failed"] += 1

            # Difficulty breakdown
            diff = r.difficulty
            if diff not in difficulty_breakdown:
                difficulty_breakdown[diff] = {"passed": 0, "failed": 0}
            if r.passed:
                difficulty_breakdown[diff]["passed"] += 1
            else:
                difficulty_breakdown[diff]["failed"] += 1

        passed_count = sum(1 for r in results if r.passed)
        avg_duration = total_duration / len(results) if results else 0.0

        return BenchmarkReport(
            benchmark_id=benchmark_id,
            agent_type=self.agent.agent_type,
            timestamp=datetime.now().isoformat(),
            total_tasks=len(results),
            passed_tasks=passed_count,
            failed_tasks=len(results) - passed_count,
            pass_rate=passed_count / len(results) if results else 0.0,
            avg_duration=avg_duration,
            results=results,
            capability_breakdown=capability_breakdown,
            template_breakdown=template_breakdown,
            difficulty_breakdown=difficulty_breakdown,
        )

    def save_report(self, report: BenchmarkReport, output_dir: Path, format: str = "json") -> Path:
        """Save benchmark report to file.

        Args:
            report: The benchmark report to save.
            output_dir: Directory to save the report.
            format: Output format ('json' or 'markdown').

        Returns:
            Path to the saved report file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        if format == "json":
            file_path = output_dir / f"{report.benchmark_id}.json"
            file_path.write_text(json.dumps(report.to_dict(), indent=2))
        else:
            file_path = output_dir / f"{report.benchmark_id}.md"
            file_path.write_text(report.to_markdown())

        return file_path
