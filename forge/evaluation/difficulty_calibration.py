"""Difficulty calibration.

Measures actual task difficulty against assigned difficulty levels
by comparing pass rates across agents and suggesting adjustments.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CalibrationResult:
    """Calibration result for a single task."""

    task_id: str
    assigned_difficulty: int
    actual_pass_rate: float
    suggested_difficulty: int
    adjustment: int = 0  # positive = harder, negative = easier
    sample_size: int = 0


class DifficultyCalibrator:
    """Calibrate task difficulty based on actual agent performance."""

    def __init__(self):
        self._calibrations: Dict[str, CalibrationResult] = {}

    def calibrate(self, task_results: List[Dict[str, Any]]) -> Dict[str, CalibrationResult]:
        """Calibrate difficulty for tasks based on run results.

        Args:
            task_results: List of dicts with keys:
                - task_id: str
                - assigned_difficulty: int (1-5)
                - passed: bool

        Returns:
            Dict mapping task_id to CalibrationResult.
        """
        # Aggregate by task
        task_stats: Dict[str, Dict[str, Any]] = {}
        for result in task_results:
            tid = result.get("task_id", "unknown")
            if tid not in task_stats:
                task_stats[tid] = {
                    "task_id": tid,
                    "assigned_difficulty": result.get("assigned_difficulty", 3),
                    "passed_count": 0,
                    "total_count": 0,
                }
            task_stats[tid]["total_count"] += 1
            if result.get("passed"):
                task_stats[tid]["passed_count"] += 1

        # Compute calibration for each task
        for tid, stats in task_stats.items():
            total = stats["total_count"]
            passed = stats["passed_count"]
            pass_rate = passed / total if total > 0 else 0.5
            assigned = stats["assigned_difficulty"]

            # Map pass rate to difficulty:
            # High pass rate (>80%) -> easier than labeled
            # Low pass rate (<20%) -> harder than labeled
            if pass_rate > 0.8:
                suggested = max(1, assigned - 1)
            elif pass_rate < 0.2:
                suggested = min(5, assigned + 1)
            else:
                suggested = assigned

            self._calibrations[tid] = CalibrationResult(
                task_id=tid,
                assigned_difficulty=assigned,
                actual_pass_rate=round(pass_rate, 3),
                suggested_difficulty=suggested,
                adjustment=suggested - assigned,
                sample_size=total,
            )

        return dict(self._calibrations)

    def get_calibration(self, task_id: str) -> Optional[CalibrationResult]:
        """Get calibration result for a specific task.

        Args:
            task_id: The task to look up.

        Returns:
            CalibrationResult or None if not found.
        """
        return self._calibrations.get(task_id)

    def suggest_adjustments(self) -> List[CalibrationResult]:
        """Get tasks where difficulty should be adjusted.

        Returns:
            List of CalibrationResult where suggested != assigned.
        """
        return [
            cr for cr in self._calibrations.values() if cr.adjustment != 0
        ]

    def get_overestimated(self) -> List[CalibrationResult]:
        """Get tasks that are easier than their assigned difficulty.

        Returns:
            List of tasks where assigned difficulty is too high.
        """
        return [cr for cr in self._calibrations.values() if cr.adjustment < 0]

    def get_underestimated(self) -> List[CalibrationResult]:
        """Get tasks that are harder than their assigned difficulty.

        Returns:
            List of tasks where assigned difficulty is too low.
        """
        return [cr for cr in self._calibrations.values() if cr.adjustment > 0]
