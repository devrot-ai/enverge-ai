"""Evaluation report export and formatting.

Provides functions to export evaluation reports in various formats
(JSON, Markdown) and format them for display.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.core.schemas import RunResult


def format_report_summary(report: dict[str, Any]) -> str:
    """Format an evaluation report summary as Markdown.

    Args:
        report: Evaluation report dictionary.

    Returns:
        Markdown-formatted summary.
    """
    summary = report.get("summary", {})
    lines = [
        f"# {report.get('title', 'Evaluation Report')}",
        "",
        f"**Report ID:** {report.get('report_id', 'N/A')}",
        f"**Generated:** {report.get('generated_at', 'N/A')}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Runs | {summary.get('total_runs', 0)} |",
        f"| Passed | {summary.get('passed', 0)} |",
        f"| Failed | {summary.get('failed', 0)} |",
        f"| Average Score | {summary.get('average_score', 0.0):.4f} |",
    ]

    # Per-task breakdown
    per_task = report.get("per_task", {})
    if per_task:
        lines.append("")
        lines.append("## Per-Task Results")
        lines.append("")
        lines.append("| Task ID | Attempts | Avg Score | Best Score | Successes |")
        lines.append("|---------|----------|-----------|------------|-----------|")
        for task_id, data in sorted(per_task.items()):
            short_id = task_id[:12] + "..." if len(task_id) > 15 else task_id
            lines.append(
                f"| {short_id} | {data.get('attempts', 0)} | "
                f"{data.get('average_score', 0.0):.4f} | "
                f"{data.get('best_score', 0.0):.4f} | "
                f"{data.get('successes', 0)} |"
            )

    return "\n".join(lines)


def export_report_json(
    report: dict[str, Any],
    filepath: Path,
) -> Path:
    """Export an evaluation report as JSON.

    Args:
        report: Evaluation report dictionary.
        filepath: Path to save the JSON file.

    Returns:
        Path to the saved file.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return filepath


def export_report_markdown(
    report: dict[str, Any],
    filepath: Path,
) -> Path:
    """Export an evaluation report as Markdown.

    Args:
        report: Evaluation report dictionary.
        filepath: Path to save the Markdown file.

    Returns:
        Path to the saved file.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    content = format_report_summary(report)
    filepath.write_text(content, encoding="utf-8")
    return filepath


def generate_run_summary(results: list[RunResult]) -> dict[str, Any]:
    """Generate a concise summary of run results.

    Args:
        results: List of run results.

    Returns:
        Dictionary with summary statistics.
    """
    if not results:
        return {
            "total_runs": 0,
            "passed": 0,
            "failed": 0,
            "success_rate": 0.0,
            "average_duration": 0.0,
        }

    passed = sum(1 for r in results if r.passed)
    durations = [r.duration_seconds for r in results if r.duration_seconds > 0]

    return {
        "total_runs": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "success_rate": passed / len(results),
        "average_duration": sum(durations) / len(durations) if durations else 0.0,
    }
