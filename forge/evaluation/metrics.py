"""Evaluation metrics computation.

Provides functions to compute success rate, pass@k, verifier quality,
and other evaluation metrics from run results.
"""

from __future__ import annotations

from typing import Any

from forge.core.schemas import FailureCategory, RunResult


def compute_success_rate(results: list[RunResult]) -> float:
    """Compute the overall success rate.

    Only counts valid completed runs (excludes infrastructure failures
    and invalid tasks from the denominator).

    Args:
        results: List of run results.

    Returns:
        Success rate between 0.0 and 1.0.
    """
    valid_runs = [
        r
        for r in results
        if r.status.value in ("completed", "failed")
        and r.diagnosis is not None
        and r.diagnosis.primary_category != FailureCategory.ENVIRONMENT_FAILURE
        and r.diagnosis.primary_category != FailureCategory.INFRASTRUCTURE_FAILURE
    ]

    if not valid_runs:
        return 0.0

    successes = sum(1 for r in valid_runs if r.passed)
    return successes / len(valid_runs)


def compute_pass_at_k(results: list[RunResult], k: int = 1) -> float:
    """Compute pass@k metric.

    pass@k estimates the probability that at least k independent
    attempts at the same task would succeed.

    Args:
        results: List of run results.
        k: Number of attempts.

    Returns:
        pass@k value between 0.0 and 1.0.
    """
    # Group results by task
    task_results: dict[str, list[bool]] = {}
    for r in results:
        if r.task_id not in task_results:
            task_results[r.task_id] = []
        task_results[r.task_id].append(r.passed)

    if not task_results:
        return 0.0

    pass_at_k_values = []
    for task_id, passed_list in task_results.items():
        n = len(passed_list)
        c = sum(passed_list)
        # Probability that none of k samples are correct
        if n >= k:
            # Estimate: (1 - c/n)^k approximates failure probability

            fail_prob = max(0.0, 1.0 - c / n)
            pass_at_k_values.append(1.0 - fail_prob**k)
        elif c > 0:
            pass_at_k_values.append(1.0)
        else:
            pass_at_k_values.append(0.0)

    return sum(pass_at_k_values) / len(pass_at_k_values)


def compute_verifier_quality(results: list[RunResult]) -> dict[str, float]:
    """Compute verifier quality metrics.

    Measures false positive and false negative rates of the verifier.

    Args:
        results: List of run results.

    Returns:
        Dictionary with verifier quality metrics.
    """
    verified = [r for r in results if r.verification is not None]

    if not verified:
        return {
            "false_positive_rate": 0.0,
            "false_negative_rate": 0.0,
            "verification_rate": 0.0,
        }

    # Verifications where agent believed success but verifier said fail
    false_positives = sum(1 for r in verified if r.agent_believes_success and not r.verification.passed)

    # Verifications where agent believed failure but verifier said pass
    false_negatives = sum(1 for r in verified if not r.agent_believes_success and r.verification.passed)

    total_believed_success = sum(1 for r in verified if r.agent_believes_success)
    total_believed_failure = sum(1 for r in verified if not r.agent_believes_success)

    return {
        "false_positive_rate": (false_positives / total_believed_success if total_believed_success > 0 else 0.0),
        "false_negative_rate": (false_negatives / total_believed_failure if total_believed_failure > 0 else 0.0),
        "verification_rate": len(verified) / len(results) if results else 0.0,
    }


def compute_failure_distribution(results: list[RunResult]) -> dict[str, int]:
    """Compute the distribution of failure categories.

    Args:
        results: List of run results.

    Returns:
        Dictionary mapping failure category to count.
    """
    distribution = {
        "agent_failure": 0,
        "environment_failure": 0,
        "invalid_task": 0,
        "verifier_failure": 0,
        "infrastructure_failure": 0,
        "uncertain": 0,
        "success": 0,
    }

    for r in results:
        if r.passed:
            distribution["success"] += 1
        elif r.diagnosis:
            category = r.diagnosis.primary_category.value
            if category in distribution:
                distribution[category] += 1

    return distribution


def compute_average_duration(results: list[RunResult]) -> float:
    """Compute average run duration.

    Args:
        results: List of run results.

    Returns:
        Average duration in seconds.
    """
    durations = [r.duration_seconds for r in results if r.duration_seconds > 0]
    if not durations:
        return 0.0
    return sum(durations) / len(durations)


def compute_metrics_summary(results: list[RunResult]) -> dict[str, Any]:
    """Compute a comprehensive metrics summary.

    Args:
        results: List of run results.

    Returns:
        Dictionary with all key metrics.
    """
    return {
        "total_runs": len(results),
        "success_rate": compute_success_rate(results),
        "pass_at_1": compute_pass_at_k(results, 1),
        "pass_at_3": compute_pass_at_k(results, 3),
        "verifier_quality": compute_verifier_quality(results),
        "failure_distribution": compute_failure_distribution(results),
        "average_duration_seconds": compute_average_duration(results),
    }
