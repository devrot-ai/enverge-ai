"""Cross-experiment result comparison.

Provides functions to compare results between different experiments
and generate comparison reports.
"""

from __future__ import annotations

from typing import Any

from forge.core.schemas import RunResult
from forge.evaluation.metrics import compute_metrics_summary


def compare_experiments(
    experiment_a_results: list[RunResult],
    experiment_b_results: list[RunResult],
    experiment_a_name: str = "Experiment A",
    experiment_b_name: str = "Experiment B",
) -> dict[str, Any]:
    """Compare results between two experiments.

    Args:
        experiment_a_results: Results from experiment A.
        experiment_b_results: Results from experiment B.
        experiment_a_name: Name of experiment A.
        experiment_b_name: Name of experiment B.

    Returns:
        Dictionary with comparison results.
    """
    metrics_a = compute_metrics_summary(experiment_a_results)
    metrics_b = compute_metrics_summary(experiment_b_results)

    return {
        "experiment_a": {
            "name": experiment_a_name,
            "metrics": metrics_a,
        },
        "experiment_b": {
            "name": experiment_b_name,
            "metrics": metrics_b,
        },
        "comparison": {
            "success_rate_diff": round(metrics_a.get("success_rate", 0.0) - metrics_b.get("success_rate", 0.0), 4),
            "pass_at_1_diff": round(metrics_a.get("pass_at_1", 0.0) - metrics_b.get("pass_at_1", 0.0), 4),
            "average_duration_diff": round(
                metrics_a.get("average_duration_seconds", 0.0) - metrics_b.get("average_duration_seconds", 0.0), 2
            ),
            "total_runs_a": metrics_a.get("total_runs", 0),
            "total_runs_b": metrics_b.get("total_runs", 0),
        },
    }


def compare_failure_distributions(
    results_a: list[RunResult],
    results_b: list[RunResult],
) -> dict[str, Any]:
    """Compare failure distributions between two experiments.

    Args:
        results_a: Results from experiment A.
        results_b: Results from experiment B.

    Returns:
        Dictionary with distribution comparison.
    """
    from forge.evaluation.metrics import compute_failure_distribution

    dist_a = compute_failure_distribution(results_a)
    dist_b = compute_failure_distribution(results_b)

    return {
        "distribution_a": dist_a,
        "distribution_b": dist_b,
        "differences": {
            category: dist_a.get(category, 0) - dist_b.get(category, 0)
            for category in set(list(dist_a.keys()) + list(dist_b.keys()))
        },
    }


def generate_comparison_report(
    experiments: dict[str, list[RunResult]],
) -> dict[str, Any]:
    """Generate a comparison report for multiple experiments.

    Args:
        experiments: Dictionary mapping experiment names to results.

    Returns:
        Dictionary with full comparison report.
    """
    report = {
        "experiments": {},
        "pairwise_comparisons": [],
    }

    # Per-experiment metrics
    for name, results in experiments.items():
        report["experiments"][name] = compute_metrics_summary(results)

    # Pairwise comparisons
    names = list(experiments.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            comparison = compare_experiments(
                experiments[names[i]],
                experiments[names[j]],
                names[i],
                names[j],
            )
            report["pairwise_comparisons"].append(comparison)

    return report
