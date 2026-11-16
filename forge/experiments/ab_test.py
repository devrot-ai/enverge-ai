"""A/B testing framework for comparing agent configurations.

Enables formal statistical comparison of two agent configurations
running on the same task set with significance testing.
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ABTestResult:
    """Result of a single run in an A/B test."""

    agent: str
    task_id: str
    passed: bool
    duration: float = 0.0
    failure_category: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent": self.agent,
            "task_id": self.task_id,
            "passed": self.passed,
            "duration": self.duration,
            "failure_category": self.failure_category,
        }


@dataclass
class ABTestReport:
    """Statistical report comparing two agents."""

    agent_a: str
    agent_b: str
    total_tasks: int
    agent_a_pass_rate: float = 0.0
    agent_b_pass_rate: float = 0.0
    agent_a_passes: int = 0
    agent_b_passes: int = 0
    p_value: float = 1.0
    statistically_significant: bool = False
    effect_size: float = 0.0
    confidence_interval_lower: float = 0.0
    confidence_interval_upper: float = 0.0
    agent_a_duration_mean: float = 0.0
    agent_b_duration_mean: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_a": self.agent_a,
            "agent_b": self.agent_b,
            "total_tasks": self.total_tasks,
            "agent_a_pass_rate": self.agent_a_pass_rate,
            "agent_b_pass_rate": self.agent_b_pass_rate,
            "agent_a_passes": self.agent_a_passes,
            "agent_b_passes": self.agent_b_passes,
            "p_value": self.p_value,
            "statistically_significant": self.statistically_significant,
            "effect_size": self.effect_size,
            "confidence_interval": {
                "lower": self.confidence_interval_lower,
                "upper": self.confidence_interval_upper,
            },
            "agent_a_duration_mean": self.agent_a_duration_mean,
            "agent_b_duration_mean": self.agent_b_duration_mean,
        }

    def to_markdown(self) -> str:
        """Generate Markdown report."""
        lines = [
            "# A/B Test Report",
            "",
            f"- **Agent A**: {self.agent_a}",
            f"- **Agent B**: {self.agent_b}",
            f"- **Total tasks**: {self.total_tasks}",
            "",
            "## Results",
            "",
            "| Metric | Agent A | Agent B |",
            "|--------|---------|---------|",
            f"| Passes | {self.agent_a_passes} | {self.agent_b_passes} |",
            f"| Pass Rate | {self.agent_a_pass_rate:.1%} | {self.agent_b_pass_rate:.1%} |",
            f"| Mean Duration | {self.agent_a_duration_mean:.2f}s | {self.agent_b_duration_mean:.2f}s |",
            "",
            "## Statistical Analysis",
            "",
            f"- **P-value**: {self.p_value:.4f}",
            f"- **Statistically significant (α=0.05)**: {'Yes' if self.statistically_significant else 'No'}",
            f"- **Effect size (Cohen's d)**: {self.effect_size:.4f}",
            f"- **95% CI**: [{self.confidence_interval_lower:.4f}, {self.confidence_interval_upper:.4f}]",
            "",
        ]
        return "\n".join(lines)


class ABTestRunner:
    """Formal A/B test runner for comparing two agent configurations.

    Runs both agents on the same task set and performs statistical
    significance testing on the results.
    """

    def __init__(self, significance_level: float = 0.05):
        """Initialize the A/B test runner.

        Args:
            significance_level: Alpha level for statistical tests (default 0.05).
        """
        self.significance_level = significance_level
        self.results_a: list[ABTestResult] = []
        self.results_b: list[ABTestResult] = []

    def add_result(self, result: ABTestResult) -> None:
        """Add a result to the appropriate agent group.

        Args:
            result: The test result to add.
        """
        if result.agent == "a":
            self.results_a.append(result)
        else:
            self.results_b.append(result)

    def run(
        self,
        agent_a_factory,
        agent_b_factory,
        tasks: list,
        run_func,
    ) -> ABTestReport:
        """Run A/B test with two agents on the same tasks.

        Args:
            agent_a_factory: Callable that creates agent A.
            agent_b_factory: Callable that creates agent B.
            tasks: List of tasks to run.
            run_func: Callable(agent, task) -> (passed, duration, failure_category).

        Returns:
            ABTestReport with statistical comparison.
        """
        self.results_a.clear()
        self.results_b.clear()

        agent_a = agent_a_factory()
        agent_b = agent_b_factory()

        for task in tasks:
            # Run agent A
            passed_a, duration_a, failure_a = run_func(agent_a, task)
            self.results_a.append(
                ABTestResult(
                    agent="a",
                    task_id=task.task_id if hasattr(task, "task_id") else str(task),
                    passed=passed_a,
                    duration=duration_a,
                    failure_category=failure_a,
                )
            )

            # Run agent B
            passed_b, duration_b, failure_b = run_func(agent_b, task)
            self.results_b.append(
                ABTestResult(
                    agent="b",
                    task_id=task.task_id if hasattr(task, "task_id") else str(task),
                    passed=passed_b,
                    duration=duration_b,
                    failure_category=failure_b,
                )
            )

        return self.generate_report(
            agent_a=agent_a.__class__.__name__ if hasattr(agent_a, "__class__") else "Agent A",
            agent_b=agent_b.__class__.__name__ if hasattr(agent_b, "__class__") else "Agent B",
        )

    def generate_report(self, agent_a: str = "Agent A", agent_b: str = "Agent B") -> ABTestReport:
        """Generate statistical comparison report.

        Args:
            agent_a: Name of agent A.
            agent_b: Name of agent B.

        Returns:
            ABTestReport with statistical analysis.
        """
        total = max(len(self.results_a), len(self.results_b), 1)

        # Pass rates
        passes_a = sum(1 for r in self.results_a if r.passed)
        passes_b = sum(1 for r in self.results_b if r.passed)
        rate_a = passes_a / len(self.results_a) if self.results_a else 0
        rate_b = passes_b / len(self.results_b) if self.results_b else 0

        # Durations
        durations_a = [r.duration for r in self.results_a if r.duration > 0]
        durations_b = [r.duration for r in self.results_b if r.duration > 0]
        mean_a = statistics.mean(durations_a) if durations_a else 0
        mean_b = statistics.mean(durations_b) if durations_b else 0

        # Statistical tests
        p_value = self._two_proportion_ztest(passes_a, len(self.results_a), passes_b, len(self.results_b))
        effect_size = self._cohens_d(self.results_a, self.results_b)
        ci_lower, ci_upper = self._confidence_interval(rate_a, rate_b)

        return ABTestReport(
            agent_a=agent_a,
            agent_b=agent_b,
            total_tasks=total,
            agent_a_pass_rate=rate_a,
            agent_b_pass_rate=rate_b,
            agent_a_passes=passes_a,
            agent_b_passes=passes_b,
            p_value=p_value,
            statistically_significant=p_value < self.significance_level,
            effect_size=effect_size,
            confidence_interval_lower=ci_lower,
            confidence_interval_upper=ci_upper,
            agent_a_duration_mean=mean_a,
            agent_b_duration_mean=mean_b,
        )

    def _two_proportion_ztest(
        self, x1: int, n1: int, x2: int, n2: int
    ) -> float:
        """Two-proportion z-test for comparing pass rates.

        Args:
            x1: Number of successes in group 1.
            n1: Total trials in group 1.
            x2: Number of successes in group 2.
            n2: Total trials in group 2.

        Returns:
            P-value for the two-tailed test.
        """
        if n1 == 0 or n2 == 0:
            return 1.0

        p1 = x1 / n1
        p2 = x2 / n2
        p_pool = (x1 + x2) / (n1 + n2)

        if p_pool == 0 or p_pool == 1:
            return 1.0

        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
        if se == 0:
            return 1.0

        z = abs(p1 - p2) / se
        # Approximate p-value from z-score using error function
        p_value = 2 * (1 - self._normal_cdf(z))
        return p_value

    def _normal_cdf(self, x: float) -> float:
        """Approximate standard normal CDF using error function.

        Args:
            x: Value to evaluate.

        Returns:
            Cumulative probability.
        """
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _cohens_d(
        self,
        results_a: list[ABTestResult],
        results_b: list[ABTestResult],
    ) -> float:
        """Calculate Cohen's d effect size for pass/fail data.

        Args:
            results_a: Results from agent A.
            results_b: Results from agent B.

        Returns:
            Cohen's d effect size.
        """
        if not results_a or not results_b:
            return 0.0

        # Convert pass/fail to 1/0
        group_a = [1.0 if r.passed else 0.0 for r in results_a]
        group_b = [1.0 if r.passed else 0.0 for r in results_b]

        mean_a = statistics.mean(group_a)
        mean_b = statistics.mean(group_b)

        # Pooled standard deviation
        var_a = statistics.variance(group_a) if len(group_a) > 1 else 0
        var_b = statistics.variance(group_b) if len(group_b) > 1 else 0

        n_a = len(group_a)
        n_b = len(group_b)

        pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
        pooled_sd = math.sqrt(pooled_var) if pooled_var > 0 else 1.0

        return (mean_a - mean_b) / pooled_sd

    def _confidence_interval(
        self,
        rate_a: float,
        rate_b: float,
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """Calculate confidence interval for difference in proportions.

        Args:
            rate_a: Pass rate of agent A.
            rate_b: Pass rate of agent B.
            confidence: Confidence level (default 0.95).

        Returns:
            Tuple of (lower_bound, upper_bound).
        """
        diff = rate_a - rate_b

        # Use sample sizes from results
        n_a = len(self.results_a) if self.results_a else 1
        n_b = len(self.results_b) if self.results_b else 1

        se = math.sqrt(rate_a * (1 - rate_a) / n_a + rate_b * (1 - rate_b) / n_b)

        # Z-score for 95% confidence
        z = 1.96 if confidence == 0.95 else 1.645

        return (diff - z * se, diff + z * se)
