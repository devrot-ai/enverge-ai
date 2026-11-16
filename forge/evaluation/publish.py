"""Benchmark publication for generating and publishing reports.

Generates Markdown reports with pass rates, timing, capability breakdown,
and baseline comparison. Maintains baseline results in YAML config.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    agent_type: str
    task_id: str
    passed: bool
    duration: float = 0.0
    failure_category: str = ""
    template: str = ""
    difficulty: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_type": self.agent_type,
            "task_id": self.task_id,
            "passed": self.passed,
            "duration": self.duration,
            "failure_category": self.failure_category,
            "template": self.template,
            "difficulty": self.difficulty,
        }


class BenchmarkPublisher:
    """Generates and publishes benchmark reports with baselines.

    Produces Markdown reports with pass rates, timing, capability breakdown,
    and regression detection against stored baselines.
    """

    def __init__(self, baselines_path: str = "configs/baselines.yaml"):
        """Initialize the benchmark publisher.

        Args:
            baselines_path: Path to baselines YAML file.
        """
        self.baselines_path = Path(baselines_path)
        self.baselines: dict[str, float] = {}
        self._load_baselines()

    def _load_baselines(self) -> None:
        """Load baselines from YAML file."""
        if self.baselines_path.exists():
            try:
                data = yaml.safe_load(self.baselines_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.baselines = data
            except yaml.YAMLError as e:
                logger.warning(f"Failed to load baselines: {e}")

    def _save_baselines(self) -> None:
        """Save baselines to YAML file."""
        self.baselines_path.parent.mkdir(parents=True, exist_ok=True)
        self.baselines_path.write_text(
            yaml.dump(self.baselines, default_flow_style=False), encoding="utf-8"
        )

    def generate_report(
        self,
        results: list[BenchmarkResult],
        agent_type: str = "",
    ) -> str:
        """Generate a Markdown report from benchmark results.

        Args:
            results: List of benchmark results.
            agent_type: Agent type for the report title.

        Returns:
            Markdown formatted report.
        """
        if not results:
            return "# Benchmark Report\n\nNo results to report.\n"

        if not agent_type:
            agent_type = results[0].agent_type

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        pass_rate = passed / total if total > 0 else 0.0

        durations = [r.duration for r in results if r.duration > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Breakdown by template
        template_stats: dict[str, dict[str, int]] = {}
        for r in results:
            if r.template not in template_stats:
                template_stats[r.template] = {"passed": 0, "total": 0}
            template_stats[r.template]["total"] += 1
            if r.passed:
                template_stats[r.template]["passed"] += 1

        # Breakdown by difficulty
        difficulty_stats: dict[int, dict[str, int]] = {}
        for r in results:
            if r.difficulty not in difficulty_stats:
                difficulty_stats[r.difficulty] = {"passed": 0, "total": 0}
            difficulty_stats[r.difficulty]["total"] += 1
            if r.passed:
                difficulty_stats[r.difficulty]["passed"] += 1

        # Failure categories
        failure_stats: dict[str, int] = {}
        for r in results:
            if not r.passed and r.failure_category:
                failure_stats[r.failure_category] = failure_stats.get(r.failure_category, 0) + 1

        # Baseline comparison
        baseline = self.baselines.get(agent_type)
        regression = ""
        if baseline is not None:
            if pass_rate < baseline - 0.05:
                regression = f"⚠️ **REGRESSION**: Pass rate {pass_rate:.1%} is below baseline {baseline:.1%}"
            elif pass_rate > baseline + 0.05:
                regression = f"✅ **IMPROVEMENT**: Pass rate {pass_rate:.1%} is above baseline {baseline:.1%}"

        lines = [
            "# Benchmark Report",
            "",
            f"- **Agent**: {agent_type}",
            f"- **Total tasks**: {total}",
            f"- **Passed**: {passed}/{total} ({pass_rate:.1%})",
            f"- **Average duration**: {avg_duration:.2f}s",
            "",
        ]

        if regression:
            lines.extend([regression, ""])

        lines.extend([
            "## Pass Rate by Template",
            "",
            "| Template | Passed | Total | Rate |",
            "|----------|--------|-------|------|",
        ])
        for template, stats in sorted(template_stats.items()):
            rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            lines.append(f"| {template} | {stats['passed']} | {stats['total']} | {rate:.1%} |")

        lines.extend([
            "",
            "## Pass Rate by Difficulty",
            "",
            "| Difficulty | Passed | Total | Rate |",
            "|------------|--------|-------|------|",
        ])
        for difficulty, stats in sorted(difficulty_stats.items()):
            rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            lines.append(f"| {difficulty} | {stats['passed']} | {stats['total']} | {rate:.1%} |")

        if failure_stats:
            lines.extend([
                "",
                "## Failure Categories",
                "",
                "| Category | Count |",
                "|----------|-------|",
            ])
            for category, count in sorted(failure_stats.items(), key=lambda x: -x[1]):
                lines.append(f"| {category} | {count} |")

        return "\n".join(lines)

    def publish(
        self,
        results: list[BenchmarkResult],
        output_dir: str = "reports/benchmark",
        agent_type: str = "",
    ) -> str:
        """Publish benchmark report to a file.

        Args:
            results: List of benchmark results.
            output_dir: Directory to write reports.
            agent_type: Agent type for the report.

        Returns:
            Path to the generated report file.
        """
        if not agent_type:
            agent_type = results[0].agent_type if results else "unknown"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate Markdown report
        report = self.generate_report(results, agent_type)
        report_file = output_path / f"{agent_type}_report.md"
        report_file.write_text(report, encoding="utf-8")

        # Generate JSON report
        json_data = {
            "agent_type": agent_type,
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "results": [r.to_dict() for r in results],
        }
        json_file = output_path / f"{agent_type}_report.json"
        json_file.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

        logger.info(f"Published benchmark report to {report_file}")
        return str(report_file)

    def compare_with_baseline(self, agent_type: str, pass_rate: float) -> str:
        """Compare current pass rate with baseline.

        Args:
            agent_type: Agent type to compare.
            pass_rate: Current pass rate.

        Returns:
            Comparison result string.
        """
        baseline = self.baselines.get(agent_type)
        if baseline is None:
            return f"No baseline for {agent_type}"

        diff = pass_rate - baseline
        if diff < -0.05:
            return f"REGRESSION: {pass_rate:.1%} vs baseline {baseline:.1%} (diff: {diff:.1%})"
        elif diff > 0.05:
            return f"IMPROVEMENT: {pass_rate:.1%} vs baseline {baseline:.1%} (diff: {diff:.1%})"
        else:
            return f"STABLE: {pass_rate:.1%} vs baseline {baseline:.1%} (diff: {diff:.1%})"

    def set_baseline(self, agent_type: str, pass_rate: float) -> None:
        """Set or update baseline for an agent type.

        Args:
            agent_type: Agent type.
            pass_rate: Baseline pass rate.
        """
        self.baselines[agent_type] = pass_rate
        self._save_baselines()

    def get_baseline(self, agent_type: str) -> Optional[float]:
        """Get baseline for an agent type.

        Args:
            agent_type: Agent type.

        Returns:
            Baseline pass rate or None.
        """
        return self.baselines.get(agent_type)
