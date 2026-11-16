"""Performance regression checks.

Tracks test execution times and detects performance regressions.
Integrated into verifier as an optional check.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PerformanceResult:
    """Result of performance measurement.

    Attributes:
        duration_seconds: Test execution time in seconds.
        baseline_seconds: Baseline execution time (from world manifest).
        regression: Whether this is a regression (slower than baseline).
        regression_factor: How much slower (1.0 = same, 2.0 = 2x slower).
        details: Human-readable summary.
    """

    duration_seconds: float = 0.0
    baseline_seconds: float | None = None
    regression: bool = False
    regression_factor: float = 1.0
    details: str = ""


class PerformanceChecker:
    """Measures test execution time and detects regressions.

    Compares against baseline stored in world manifest metadata.
    """

    def __init__(self, regression_threshold: float = 2.0):
        """Initialize the performance checker.

        Args:
            regression_threshold: Factor above baseline to flag as regression.
        """
        self.regression_threshold = regression_threshold

    def measure(self, workspace_dir: Path, baseline_seconds: float | None = None) -> PerformanceResult:
        """Measure test execution time.

        Args:
            workspace_dir: Path to the agent's workspace.
            baseline_seconds: Optional baseline time in seconds.

        Returns:
            PerformanceResult with timing data and regression flag.
        """
        result = PerformanceResult()
        result.baseline_seconds = baseline_seconds

        # Measure public test execution time
        test_file = workspace_dir / "tests" / "test_public.py"
        if not test_file.exists():
            result.details = "No public tests found"
            return result

        start = time.time()
        try:
            subprocess.run(
                ["python", "-m", "pytest", str(test_file), "-q"],
                cwd=workspace_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            result.details = "Test execution timed out"
            return result

        result.duration_seconds = round(time.time() - start, 3)

        # Compare against baseline
        if baseline_seconds and baseline_seconds > 0:
            result.regression_factor = round(result.duration_seconds / baseline_seconds, 2)
            result.regression = result.regression_factor >= self.regression_threshold

            if result.regression:
                result.details = (
                    f"Performance regression: {result.regression_factor}x slower "
                    f"({result.duration_seconds}s vs {baseline_seconds}s baseline)"
                )
            else:
                result.details = (
                    f"No regression: {result.regression_factor}x baseline "
                    f"({result.duration_seconds}s vs {baseline_seconds}s)"
                )
        else:
            result.details = f"Test execution: {result.duration_seconds}s (no baseline)"

        return result

    def get_baseline(self, world_metadata: dict) -> float | None:
        """Extract baseline from world metadata.

        Args:
            world_metadata: World spec metadata dict.

        Returns:
            Baseline execution time in seconds, or None.
        """
        return world_metadata.get("baseline_test_seconds")
