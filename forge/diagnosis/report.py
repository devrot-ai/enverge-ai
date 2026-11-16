"""Diagnosis report generation and formatting.

Creates human-readable diagnosis reports from FailureDiagnosis objects.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from forge.core.schemas import FailureCategory, FailureDiagnosis, RunResult


def create_diagnosis_report(result: RunResult) -> dict[str, Any]:
    """Create a diagnosis report from a run result.

    Args:
        result: The run result to diagnose.

    Returns:
        Dictionary with diagnosis report.
    """
    from forge.diagnosis.triage import triage_run

    triage = triage_run(result)

    report = {
        "run_id": result.run_id,
        "task_id": result.task_id,
        "agent_id": result.agent_id,
        "generated_at": datetime.utcnow().isoformat(),
        "outcome": "passed" if result.passed else "failed",
        "diagnosis": {
            "primary_category": triage["primary_category"],
            "confidence": triage["confidence"],
            "supporting_evidence": triage["evidence"].get("supporting", {}),
            "contradictory_evidence": triage["evidence"].get("contradictory", {}),
        },
        "run_details": {
            "status": result.status.value,
            "duration_seconds": result.duration_seconds,
            "step_count": result.step_count,
            "agent_made_changes": result.agent_made_changes,
            "agent_believes_success": result.agent_believes_success,
            "error": result.error,
        },
        "verification": (
            {
                "public_tests_ran": result.verification.public_tests_ran if result.verification else False,
                "public_tests_passed": result.verification.public_tests_passed if result.verification else False,
                "hidden_tests_ran": result.verification.hidden_tests_ran if result.verification else False,
                "hidden_tests_passed": result.verification.hidden_tests_passed if result.verification else False,
            }
            if result.verification
            else None
        ),
    }

    # Add recommended action
    category = triage["primary_category"]
    report["diagnosis"]["recommended_action"] = get_recommended_action(category)

    return report


def get_recommended_action(category: str) -> str:
    """Get recommended action for a failure category.

    Args:
        category: Failure category string.

    Returns:
        Recommended action string.
    """
    actions = {
        "agent_failure": "Preserve as learning signal; generate related tasks targeting this weakness",
        "environment_failure": "Quarantine the run; repair the environment; revalidate and rerun",
        "invalid_task": "Reject or revise the task specification; revalidate before reuse",
        "verifier_failure": "Repair the verifier; rerun the full affected task set",
        "infrastructure_failure": "Retry the run or abort if persistent",
        "uncertain": "Manual review required; collect more evidence",
    }
    return actions.get(category, "Review the run manually")


def format_diagnosis_summary(diagnosis: FailureDiagnosis) -> str:
    """Format a diagnosis as a human-readable summary.

    Args:
        diagnosis: The diagnosis to format.

    Returns:
        Human-readable summary string.
    """
    category = diagnosis.primary_category
    if isinstance(category, FailureCategory):
        category_str = category.value
    else:
        category_str = str(category)

    lines = [
        f"## Diagnosis: {category_str}",
        "",
        f"**Confidence:** {diagnosis.confidence:.2%}",
        f"**Component:** {diagnosis.affected_component or 'Unknown'}",
        f"**Action:** {diagnosis.recommended_action}",
    ]

    if diagnosis.supporting_evidence:
        lines.append("")
        lines.append("**Supporting Evidence:**")
        for evidence in diagnosis.supporting_evidence:
            lines.append(f"- {evidence}")

    if diagnosis.contradictory_evidence:
        lines.append("")
        lines.append("**Contradictory Evidence:**")
        for evidence in diagnosis.contradictory_evidence:
            lines.append(f"- {evidence}")

    return "\n".join(lines)


def batch_diagnose(results: list[RunResult]) -> list[dict[str, Any]]:
    """Diagnose multiple run results in batch.

    Args:
        results: List of run results.

    Returns:
        List of diagnosis reports.
    """
    return [create_diagnosis_report(r) for r in results]


def summarize_diagnoses(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize a batch of diagnosis reports.

    Args:
        reports: List of diagnosis reports.

    Returns:
        Summary with category counts and average confidence.
    """
    category_counts = {}
    total_confidence = 0.0
    count = 0

    for report in reports:
        category = report["diagnosis"]["primary_category"]
        category_counts[category] = category_counts.get(category, 0) + 1
        total_confidence += report["diagnosis"]["confidence"]
        count += 1

    return {
        "total_diagnosed": count,
        "category_distribution": category_counts,
        "average_confidence": total_confidence / count if count > 0 else 0.0,
    }
