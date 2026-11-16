"""Evaluation report generator.

Produces comprehensive Markdown/JSON reports with pass rates,
failure breakdowns, timing analysis, and capability heatmaps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from forge.core.schemas import RunResult, TaskSpec

logger = logging.getLogger(__name__)


@dataclass
class EvaluationStats:
    """Statistics for evaluation report."""

    total_runs: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    avg_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    failure_categories: dict[str, int] = field(default_factory=dict)
    template_pass_rates: dict[str, float] = field(default_factory=dict)
    agent_pass_rates: dict[str, float] = field(default_factory=dict)
    difficulty_pass_rates: dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total_runs": self.total_runs,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 4),
            "avg_duration": round(self.avg_duration, 2),
            "min_duration": round(self.min_duration, 2),
            "max_duration": round(self.max_duration, 2),
            "failure_categories": self.failure_categories,
            "template_pass_rates": {k: round(v, 4) for k, v in self.template_pass_rates.items()},
            "agent_pass_rates": {k: round(v, 4) for k, v in self.agent_pass_rates.items()},
            "difficulty_pass_rates": {str(k): round(v, 4) for k, v in self.difficulty_pass_rates.items()},
        }


class EvaluationReport:
    """Generate comprehensive evaluation reports.

    Produces Markdown and JSON reports with:
    - Pass rates by template, mutation, difficulty, agent
    - Failure category breakdown
    - Timing analysis
    - Capability heatmap
    - Statistical summary
    - Recommendations
    """

    def __init__(self):
        """Initialize the report generator."""
        pass

    def generate(
        self,
        run_results: list[RunResult],
        task_specs: list[TaskSpec],
    ) -> EvaluationStats:
        """Generate evaluation statistics from run results.

        Args:
            run_results: List of run results.
            task_specs: List of task specifications.

        Returns:
            EvaluationStats with comprehensive statistics.
        """
        stats = EvaluationStats()
        stats.total_runs = len(run_results)

        if not run_results:
            return stats

        # Calculate pass/fail
        durations = []
        template_stats: dict[str, dict[str, int]] = {}
        agent_stats: dict[str, dict[str, int]] = {}
        difficulty_stats: dict[int, dict[str, int]] = {}

        for run_result, task_spec in zip(run_results, task_specs):
            if run_result.passed:
                stats.passed += 1
            else:
                stats.failed += 1

            durations.append(run_result.duration_seconds)

            # Template stats
            template_name = ""
            if task_spec.metadata:
                template_name = task_spec.metadata.get("template_name", "unknown")
            if template_name not in template_stats:
                template_stats[template_name] = {"passed": 0, "total": 0}
            template_stats[template_name]["total"] += 1
            if run_result.passed:
                template_stats[template_name]["passed"] += 1

            # Agent stats
            agent_type = run_result.agent_id or "unknown"
            if agent_type not in agent_stats:
                agent_stats[agent_type] = {"passed": 0, "total": 0}
            agent_stats[agent_type]["total"] += 1
            if run_result.passed:
                agent_stats[agent_type]["passed"] += 1

            # Difficulty stats
            difficulty = task_spec.difficulty_level or 1
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {"passed": 0, "total": 0}
            difficulty_stats[difficulty]["total"] += 1
            if run_result.passed:
                difficulty_stats[difficulty]["passed"] += 1

            # Failure categories
            if not run_result.passed and run_result.diagnosis:
                category = (
                    run_result.diagnosis.primary_category.value
                    if hasattr(run_result.diagnosis.primary_category, "value")
                    else str(run_result.diagnosis.primary_category)
                )
                stats.failure_categories[category] = (
                    stats.failure_categories.get(category, 0) + 1
                )

        # Calculate rates
        stats.pass_rate = stats.passed / stats.total_runs if stats.total_runs > 0 else 0.0

        if durations:
            stats.avg_duration = sum(durations) / len(durations)
            stats.min_duration = min(durations)
            stats.max_duration = max(durations)

        # Template pass rates
        for template, s in template_stats.items():
            stats.template_pass_rates[template] = s["passed"] / s["total"] if s["total"] > 0 else 0.0

        # Agent pass rates
        for agent, s in agent_stats.items():
            stats.agent_pass_rates[agent] = s["passed"] / s["total"] if s["total"] > 0 else 0.0

        # Difficulty pass rates
        for difficulty, s in difficulty_stats.items():
            stats.difficulty_pass_rates[difficulty] = (
                s["passed"] / s["total"] if s["total"] > 0 else 0.0
            )

        return stats

    def generate_markdown(self, stats: EvaluationStats) -> str:
        """Generate a Markdown report from evaluation stats.

        Args:
            stats: Evaluation statistics.

        Returns:
            Markdown formatted report.
        """
        lines = [
            "# Evaluation Report",
            "",
            f"**Generated**: {datetime.utcnow().isoformat()}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Runs | {stats.total_runs} |",
            f"| Passed | {stats.passed} |",
            f"| Failed | {stats.failed} |",
            f"| Pass Rate | {stats.pass_rate:.1%} |",
            f"| Avg Duration | {stats.avg_duration:.2f}s |",
            f"| Min Duration | {stats.min_duration:.2f}s |",
            f"| Max Duration | {stats.max_duration:.2f}s |",
            "",
        ]

        # Failure categories
        if stats.failure_categories:
            lines.append("## Failure Categories")
            lines.append("")
            lines.append("| Category | Count | Percentage |")
            lines.append("|----------|-------|------------|")
            for category, count in sorted(
                stats.failure_categories.items(), key=lambda x: -x[1]
            ):
                pct = count / stats.total_runs * 100 if stats.total_runs > 0 else 0
                lines.append(f"| {category} | {count} | {pct:.1f}% |")
            lines.append("")

        # Template pass rates
        if stats.template_pass_rates:
            lines.append("## Pass Rate by Template")
            lines.append("")
            lines.append("| Template | Pass Rate |")
            lines.append("|----------|-----------|")
            for template, rate in sorted(
                stats.template_pass_rates.items(), key=lambda x: -x[1]
            ):
                lines.append(f"| {template} | {rate:.1%} |")
            lines.append("")

        # Agent pass rates
        if stats.agent_pass_rates:
            lines.append("## Pass Rate by Agent")
            lines.append("")
            lines.append("| Agent | Pass Rate |")
            lines.append("|-------|-----------|")
            for agent, rate in sorted(
                stats.agent_pass_rates.items(), key=lambda x: -x[1]
            ):
                lines.append(f"| {agent} | {rate:.1%} |")
            lines.append("")

        # Difficulty pass rates
        if stats.difficulty_pass_rates:
            lines.append("## Pass Rate by Difficulty")
            lines.append("")
            lines.append("| Difficulty | Pass Rate |")
            lines.append("|------------|-----------|")
            for difficulty, rate in sorted(stats.difficulty_pass_rates.items()):
                lines.append(f"| {difficulty} | {rate:.1%} |")
            lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")
        lines.extend(self._generate_recommendations(stats))

        return "\n".join(lines)

    def _generate_recommendations(self, stats: EvaluationStats) -> list[str]:
        """Generate recommendations based on evaluation stats.

        Args:
            stats: Evaluation statistics.

        Returns:
            List of recommendation strings.
        """
        recommendations = []

        # Low overall pass rate
        if stats.pass_rate < 0.3:
            recommendations.append(
                "- **Low overall pass rate**: Consider easier tasks or better agents."
            )

        # High overall pass rate
        if stats.pass_rate > 0.9:
            recommendations.append(
                "- **High overall pass rate**: Consider increasing task difficulty."
            )

        # Template-specific issues
        for template, rate in stats.template_pass_rates.items():
            if rate < 0.2:
                recommendations.append(
                    f"- **Template '{template}' has low pass rate ({rate:.1%})**: "
                    f"Review task generation for this template."
                )

        # Failure category analysis
        if stats.failure_categories:
            most_common = max(stats.failure_categories, key=stats.failure_categories.get)
            count = stats.failure_categories[most_common]
            if count > stats.total_runs * 0.3:
                recommendations.append(
                    f"- **Most common failure: '{most_common}' ({count} times)**: "
                    f"Focus on improving agent handling of this failure type."
                )

        # Difficulty analysis
        for difficulty, rate in stats.difficulty_pass_rates.items():
            if rate < 0.1 and difficulty > 1:
                recommendations.append(
                    f"- **Difficulty {difficulty} has very low pass rate ({rate:.1%})**: "
                    f"Tasks may be too hard for current agents."
                )

        if not recommendations:
            recommendations.append("- No specific recommendations. Performance looks balanced.")

        return recommendations

    def generate_json(self, stats: EvaluationStats) -> dict[str, Any]:
        """Generate a JSON report from evaluation stats.

        Args:
            stats: Evaluation statistics.

        Returns:
            Dictionary with full report data.
        """
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "stats": stats.to_dict(),
            "recommendations": self._generate_recommendations(stats),
        }
