"""Task scoring and evaluation report generation.

Provides functions to score individual task runs and generate
versioned evaluation reports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from forge.core.schemas import RunResult


def score_run(result: RunResult) -> float:
    """Score a single run on a 0-1 scale.

    Scoring considers:
    - Whether the task was passed (0.5 weight)
    - Whether existing tests still pass (0.2 weight)
    - Whether the agent made changes (0.1 weight)
    - Verification completeness (0.2 weight)

    Args:
        result: The run result to score.

    Returns:
        Score between 0.0 and 1.0.
    """
    score = 0.0

    # Task passed (50%)
    if result.passed:
        score += 0.5

    # Existing tests still pass (20%)
    if result.verification and result.verification.existing_tests_passed:
        score += 0.2

    # Agent made changes (10%)
    if result.agent_made_changes:
        score += 0.1

    # Verification completeness (20%)
    if result.verification:
        v = result.verification
        completeness = 0.0
        checks = 0
        if v.public_tests_ran:
            checks += 1
            completeness += 1.0
        if v.hidden_tests_ran:
            checks += 1
            completeness += 1.0
        if v.reference_solution_checked:
            checks += 1
            completeness += 1.0
        if v.initial_defect_checked:
            checks += 1
            completeness += 1.0
        if checks > 0:
            score += 0.2 * (completeness / checks)

    return min(1.0, score)


def score_task_results(task_id: str, results: list[RunResult]) -> dict[str, Any]:
    """Score all results for a specific task.

    Args:
        task_id: The task ID to score.
        results: List of all run results.

    Returns:
        Dictionary with task-level scores.
    """
    task_results = [r for r in results if r.task_id == task_id]

    if not task_results:
        return {
            "task_id": task_id,
            "attempts": 0,
            "average_score": 0.0,
            "best_score": 0.0,
            "successes": 0,
        }

    scores = [score_run(r) for r in task_results]

    return {
        "task_id": task_id,
        "attempts": len(task_results),
        "average_score": sum(scores) / len(scores),
        "best_score": max(scores),
        "successes": sum(1 for r in task_results if r.passed),
        "scores": scores,
    }


def generate_evaluation_report(
    results: list[RunResult],
    report_id: str | None = None,
    title: str = "Evaluation Report",
) -> dict[str, Any]:
    """Generate a versioned evaluation report.

    Args:
        results: List of run results.
        report_id: Optional report ID.
        title: Report title.

    Returns:
        Dictionary with evaluation report.
    """
    from forge.core.schemas import generate_id

    report = {
        "report_id": report_id or generate_id("report-"),
        "title": title,
        "schema_version": "1.0",
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_runs": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "average_score": (sum(score_run(r) for r in results) / len(results) if results else 0.0),
        },
        "per_task": {},
        "per_agent": {},
    }

    # Per-task scores
    task_ids = set(r.task_id for r in results)
    for task_id in task_ids:
        report["per_task"][task_id] = score_task_results(task_id, results)

    # Per-agent scores
    agent_ids = set(r.agent_id for r in results)
    for agent_id in agent_ids:
        agent_results = [r for r in results if r.agent_id == agent_id]
        scores = [score_run(r) for r in agent_results]
        report["per_agent"][agent_id] = {
            "attempts": len(agent_results),
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "successes": sum(1 for r in agent_results if r.passed),
        }

    return report


class EvaluationReport:
    """Versioned evaluation report with comparison support.

    Attributes:
        report_id: Unique report identifier.
        title: Human-readable title.
        schema_version: Report schema version.
        generated_at: Timestamp of generation.
        data: Report data dictionary.
    """

    def __init__(
        self,
        title: str = "Evaluation Report",
        report_id: str | None = None,
    ):
        from forge.core.schemas import generate_id

        self.report_id = report_id or generate_id("report-")
        self.title = title
        self.schema_version = "1.0"
        self.generated_at: str | None = None
        self.data: dict[str, Any] = {}

    def generate(self, results: list[RunResult]) -> EvaluationReport:
        """Generate the report from run results.

        Args:
            results: List of run results.

        Returns:
            Self for chaining.
        """
        self.data = generate_evaluation_report(results, self.report_id, self.title)
        return self

    def compare_with(self, other: EvaluationReport) -> dict[str, Any]:
        """Compare this report with another.

        Args:
            other: Another evaluation report.

        Returns:
            Dictionary with comparison results.
        """
        if not self.data or not other.data:
            return {"error": "Reports not generated"}

        self_summary = self.data.get("summary", {})
        other_summary = other.data.get("summary", {})

        return {
            "report_a": {
                "id": self.report_id,
                "title": self.title,
                "summary": self_summary,
            },
            "report_b": {
                "id": other.report_id,
                "title": other.title,
                "summary": other_summary,
            },
            "differences": {
                "total_runs": (self_summary.get("total_runs", 0) - other_summary.get("total_runs", 0)),
                "passed": (self_summary.get("passed", 0) - other_summary.get("passed", 0)),
                "average_score": round(
                    self_summary.get("average_score", 0.0) - other_summary.get("average_score", 0.0),
                    4,
                ),
            },
        }

    def to_dict(self) -> dict[str, Any]:
        """Export report as dictionary.

        Returns:
            Report data dictionary.
        """
        return self.data
