"""Capability tracking for the adaptive curriculum engine.

Tracks per-capability performance across runs to identify
agent strengths and weaknesses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from forge.core.schemas import RunResult


class CapabilityRecord:
    """Performance record for a single capability.

    Attributes:
        name: Capability name (e.g. "debugging", "edge_case_reasoning").
        attempts: Total number of attempts.
        successes: Number of successful attempts.
        failures: Number of failed attempts.
        recent_performance: Last N results (True/False).
        difficulty_levels: List of difficulty levels attempted.
        first_seen: When this capability was first tracked.
        last_updated: When this record was last updated.
    """

    def __init__(self, name: str):
        self.name = name
        self.attempts = 0
        self.successes = 0
        self.failures = 0
        self.recent_performance: list[bool] = []
        self.difficulty_levels: list[int] = []
        self.first_seen = datetime.utcnow().isoformat()
        self.last_updated = self.first_seen

    @property
    def success_rate(self) -> float:
        """Compute the success rate for this capability.

        Returns:
            Success rate between 0.0 and 1.0.
        """
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts

    @property
    def recent_success_rate(self, window: int = 5) -> float:
        """Compute recent success rate over a sliding window.

        Args:
            window: Number of recent attempts to consider.

        Returns:
            Recent success rate.
        """
        recent = self.recent_performance[-window:]
        if not recent:
            return 0.0
        return sum(recent) / len(recent)

    @property
    def average_difficulty(self) -> float:
        """Compute average difficulty level attempted.

        Returns:
            Average difficulty.
        """
        if not self.difficulty_levels:
            return 0.0
        return sum(self.difficulty_levels) / len(self.difficulty_levels)

    @property
    def confidence_estimate(self) -> float:
        """Estimate confidence in the success rate.

        Uses a simple Bayesian estimate with a uniform prior.

        Returns:
            Confidence-adjusted success rate.
        """
        # Laplace smoothing: (successes + 1) / (attempts + 2)
        return (self.successes + 1) / (self.attempts + 2)

    def update(self, success: bool, difficulty: int = 1) -> None:
        """Update the record with a new result.

        Args:
            success: Whether the attempt was successful.
            difficulty: Difficulty level of the task.
        """
        self.attempts += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        self.recent_performance.append(success)
        self.difficulty_levels.append(difficulty)
        self.last_updated = datetime.utcnow().isoformat()

    def is_weakness(self, threshold: float = 0.4, min_attempts: int = 3) -> bool:
        """Check if this capability is a weakness.

        Args:
            threshold: Success rate below which it's considered weak.
            min_attempts: Minimum attempts needed to judge.

        Returns:
            True if this is a weakness.
        """
        if self.attempts < min_attempts:
            return False
        return self.success_rate < threshold

    def to_dict(self) -> dict[str, Any]:
        """Export record as dictionary.

        Returns:
            Dictionary with capability data.
        """
        return {
            "name": self.name,
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.success_rate, 4),
            "recent_success_rate": round(self.recent_success_rate(), 4),
            "average_difficulty": round(self.average_difficulty, 2),
            "confidence_estimate": round(self.confidence_estimate, 4),
            "is_weakness": self.is_weakness(),
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
        }


class CapabilityTracker:
    """Tracks performance across multiple capabilities.

    Maintains CapabilityRecord instances for each tracked capability
    and provides methods to update and query performance.
    """

    DEFAULT_CAPABILITIES = [
        "debugging",
        "edge_case_reasoning",
        "testing",
        "code_navigation",
        "regression_analysis",
        "api_design",
    ]

    def __init__(self, capabilities: list[str] | None = None):
        self.capabilities: dict[str, CapabilityRecord] = {}
        caps = capabilities or self.DEFAULT_CAPABILITIES
        for cap in caps:
            self.capabilities[cap] = CapabilityRecord(cap)

    def update_from_result(
        self,
        result: RunResult,
        capabilities: list[str] | None = None,
    ) -> None:
        """Update capability records from a run result.

        Args:
            result: The run result.
            capabilities: List of capabilities this task exercises.
        """
        caps = capabilities or result.metadata.get("capabilities", [])
        if not caps:
            return

        success = result.passed
        difficulty = result.metadata.get("difficulty_level", 1)

        for cap in caps:
            if cap not in self.capabilities:
                self.capabilities[cap] = CapabilityRecord(cap)
            self.capabilities[cap].update(success, difficulty)

    def get_weaknesses(
        self,
        threshold: float = 0.4,
        min_attempts: int = 3,
    ) -> list[str]:
        """Get list of capability weaknesses.

        Args:
            threshold: Success rate threshold.
            min_attempts: Minimum attempts to judge.

        Returns:
            List of weak capability names.
        """
        weaknesses = []
        for cap, record in self.capabilities.items():
            if record.is_weakness(threshold, min_attempts):
                weaknesses.append(cap)
        return weaknesses

    def get_strongest(self) -> str | None:
        """Get the strongest capability.

        Returns:
            Name of the strongest capability, or None if no data.
        """
        best = None
        best_rate = -1.0
        for cap, record in self.capabilities.items():
            if record.attempts > 0 and record.success_rate > best_rate:
                best_rate = record.success_rate
                best = cap
        return best

    def get_scores(self) -> dict[str, float]:
        """Get success rate scores for all capabilities.

        Returns:
            Dictionary mapping capability names to scores.
        """
        return {cap: record.confidence_estimate for cap, record in self.capabilities.items()}

    def to_dict(self) -> dict[str, Any]:
        """Export all capability records.

        Returns:
            Dictionary with all capability data.
        """
        return {cap: record.to_dict() for cap, record in self.capabilities.items()}

    def add_capability(self, name: str) -> None:
        """Add a new capability to track.

        Args:
            name: Capability name.
        """
        if name not in self.capabilities:
            self.capabilities[name] = CapabilityRecord(name)
