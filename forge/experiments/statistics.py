"""Statistical analysis for experiment results.

Provides t-tests, effect sizes, confidence intervals, and chi-square
tests for comparing experiment outcomes. Falls back to manual calculations
when scipy is not available.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StatisticalResult:
    """Result of a statistical test."""

    test_name: str
    statistic: float = 0.0
    p_value: float = 1.0
    significant: bool = False
    alpha: float = 0.05
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "test_name": self.test_name,
            "statistic": round(self.statistic, 6),
            "p_value": round(self.p_value, 6),
            "significant": self.significant,
            "alpha": self.alpha,
            "details": self.details,
        }


class StatisticalAnalyzer:
    """Perform statistical analysis on experiment results.

    Uses scipy if available, falls back to manual calculations.
    """

    def __init__(self, alpha: float = 0.05):
        """Initialize the analyzer.

        Args:
            alpha: Significance level for hypothesis tests.
        """
        self.alpha = alpha
        self._has_scipy = False
        try:
            from scipy import stats  # noqa: F401

            self._has_scipy = True
        except ImportError:
            pass

    def ttest(
        self,
        group_a: list[float],
        group_b: list[float],
        two_tailed: bool = True,
    ) -> StatisticalResult:
        """Perform an independent two-sample t-test.

        Args:
            group_a: First group of values.
            group_b: Second group of values.
            two_tailed: Whether to perform a two-tailed test.

        Returns:
            StatisticalResult with t-statistic and p-value.
        """
        if len(group_a) < 2 or len(group_b) < 2:
            return StatisticalResult(
                test_name="t-test",
                details={"error": "Each group needs at least 2 samples"},
            )

        if self._has_scipy:
            return self._ttest_scipy(group_a, group_b, two_tailed)
        else:
            return self._ttest_manual(group_a, group_b, two_tailed)

    def effect_size(
        self,
        group_a: list[float],
        group_b: list[float],
    ) -> StatisticalResult:
        """Calculate Cohen's d effect size.

        Args:
            group_a: First group of values.
            group_b: Second group of values.

        Returns:
            StatisticalResult with effect size and interpretation.
        """
        mean_a = sum(group_a) / len(group_a)
        mean_b = sum(group_b) / len(group_b)

        var_a = sum((x - mean_a) ** 2 for x in group_a) / (len(group_a) - 1)
        var_b = sum((x - mean_b) ** 2 for x in group_b) / (len(group_b) - 1)

        n_a = len(group_a)
        n_b = len(group_b)

        # Pooled standard deviation
        pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
        pooled_std = math.sqrt(pooled_var) if pooled_var > 0 else 1.0

        d = (mean_a - mean_b) / pooled_std

        # Interpret effect size
        abs_d = abs(d)
        if abs_d < 0.2:
            interpretation = "negligible"
        elif abs_d < 0.5:
            interpretation = "small"
        elif abs_d < 0.8:
            interpretation = "medium"
        else:
            interpretation = "large"

        return StatisticalResult(
            test_name="cohens_d",
            statistic=d,
            details={
                "interpretation": interpretation,
                "mean_a": round(mean_a, 4),
                "mean_b": round(mean_b, 4),
                "pooled_std": round(pooled_std, 4),
            },
        )

    def confidence_interval(
        self,
        values: list[float],
        confidence: float = 0.95,
    ) -> StatisticalResult:
        """Calculate a confidence interval for the mean.

        Args:
            values: Sample values.
            confidence: Confidence level (0.0-1.0).

        Returns:
            StatisticalResult with confidence interval bounds.
        """
        if not values:
            return StatisticalResult(
                test_name="confidence_interval",
                details={"error": "No values provided"},
            )

        n = len(values)
        mean = sum(values) / n

        if n < 2:
            return StatisticalResult(
                test_name="confidence_interval",
                statistic=mean,
                details={"ci_lower": mean, "ci_upper": mean, "n": n},
            )

        std = math.sqrt(sum((x - mean) ** 2 for x in values) / (n - 1))
        se = std / math.sqrt(n)

        # Use z-score approximation for large samples, t-approximation for small
        if n >= 30:
            if confidence == 0.95:
                z = 1.96
            elif confidence == 0.99:
                z = 2.576
            else:
                z = 1.96  # Default to 95%
        else:
            # Approximate t-value for small samples
            t_values = {
                2: 12.706,
                3: 4.303,
                4: 3.182,
                5: 2.776,
                6: 2.447,
                7: 2.365,
                8: 2.306,
                9: 2.262,
                10: 2.228,
                15: 2.131,
                20: 2.086,
                25: 2.060,
            }
            t = t_values.get(n, 2.048)  # Default for n=26-29
            z = t if confidence == 0.95 else t * 1.3  # Approximate for 99%

        margin = z * se
        ci_lower = mean - margin
        ci_upper = mean + margin

        return StatisticalResult(
            test_name="confidence_interval",
            statistic=mean,
            details={
                "ci_lower": round(ci_lower, 4),
                "ci_upper": round(ci_upper, 4),
                "margin_of_error": round(margin, 4),
                "std": round(std, 4),
                "se": round(se, 4),
                "n": n,
                "confidence": confidence,
            },
        )

    def chi_square(
        self,
        observed: list[int],
        expected: list[int] | None = None,
    ) -> StatisticalResult:
        """Perform a chi-square goodness-of-fit test.

        Args:
            observed: Observed frequencies.
            expected: Expected frequencies. If None, assumes uniform distribution.

        Returns:
            StatisticalResult with chi-square statistic and p-value.
        """
        if not observed:
            return StatisticalResult(
                test_name="chi_square",
                details={"error": "No observed values"},
            )

        if expected is None:
            total = sum(observed)
            expected = [total / len(observed)] * len(observed)

        if len(observed) != len(expected):
            return StatisticalResult(
                test_name="chi_square",
                details={"error": "Observed and expected must have same length"},
            )

        # Calculate chi-square statistic
        chi2 = 0.0
        for o, e in zip(observed, expected):
            if e > 0:
                chi2 += (o - e) ** 2 / e

        # Degrees of freedom
        df = len(observed) - 1

        # Approximate p-value using Wilson-Hilferty transformation
        p_value = self._chi_square_p_value(chi2, df)

        return StatisticalResult(
            test_name="chi_square",
            statistic=chi2,
            p_value=p_value,
            significant=p_value < self.alpha,
            alpha=self.alpha,
            details={
                "df": df,
                "observed": observed,
                "expected": [round(e, 2) for e in expected],
            },
        )

    def generate_report(
        self,
        group_a: list[float],
        group_b: list[float],
        name_a: str = "Group A",
        name_b: str = "Group B",
    ) -> dict[str, Any]:
        """Generate a comprehensive statistical comparison report.

        Args:
            group_a: First group of values.
            group_b: Second group of values.
            name_a: Name for group A.
            name_b: Name for group B.

        Returns:
            Report dictionary with all statistical tests.
        """
        ttest_result = self.ttest(group_a, group_b)
        effect_result = self.effect_size(group_a, group_b)
        ci_a = self.confidence_interval(group_a)
        ci_b = self.confidence_interval(group_b)

        return {
            "groups": {
                name_a: {
                    "n": len(group_a),
                    "mean": round(sum(group_a) / len(group_a), 4) if group_a else 0,
                    "std": round(
                        math.sqrt(
                            sum((x - sum(group_a) / len(group_a)) ** 2 for x in group_a)
                            / (len(group_a) - 1)
                        )
                        if len(group_a) >= 2
                        else 0,
                        4,
                    ),
                    "confidence_interval": ci_a.details,
                },
                name_b: {
                    "n": len(group_b),
                    "mean": round(sum(group_b) / len(group_b), 4) if group_b else 0,
                    "std": round(
                        math.sqrt(
                            sum((x - sum(group_b) / len(group_b)) ** 2 for x in group_b)
                            / (len(group_b) - 1)
                        )
                        if len(group_b) >= 2
                        else 0,
                        4,
                    ),
                    "confidence_interval": ci_b.details,
                },
            },
            "tests": {
                "ttest": ttest_result.to_dict(),
                "effect_size": effect_result.to_dict(),
            },
            "summary": self._generate_summary(ttest_result, effect_result),
        }

    def _generate_summary(
        self,
        ttest_result: StatisticalResult,
        effect_result: StatisticalResult,
    ) -> str:
        """Generate a human-readable summary of the statistical tests.

        Args:
            ttest_result: T-test result.
            effect_result: Effect size result.

        Returns:
            Markdown-formatted summary.
        """
        lines = []
        lines.append("## Statistical Analysis Summary")
        lines.append("")

        if ttest_result.p_value < self.alpha:
            lines.append(
                f"- **T-test**: Statistically significant (t={ttest_result.statistic:.4f}, "
                f"p={ttest_result.p_value:.4f})"
            )
        else:
            lines.append(
                f"- **T-test**: Not statistically significant (t={ttest_result.statistic:.4f}, "
                f"p={ttest_result.p_value:.4f})"
            )

        interpretation = effect_result.details.get("interpretation", "unknown")
        lines.append(
            f"- **Effect size**: Cohen's d = {effect_result.statistic:.4f} ({interpretation})"
        )
        lines.append("")

        if ttest_result.significant and abs(effect_result.statistic) >= 0.5:
            lines.append("Conclusion: There is a statistically significant difference between groups.")
        elif ttest_result.significant:
            lines.append(
                "Conclusion: There is a statistically significant difference, "
                "but the effect size is small."
            )
        else:
            lines.append(
                "Conclusion: No statistically significant difference detected between groups."
            )

        return "\n".join(lines)

    def _ttest_scipy(
        self,
        group_a: list[float],
        group_b: list[float],
        two_tailed: bool = True,
    ) -> StatisticalResult:
        """T-test using scipy."""
        from scipy import stats

        stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)
        return StatisticalResult(
            test_name="t-test",
            statistic=stat,
            p_value=p_value,
            significant=p_value < self.alpha,
            alpha=self.alpha,
            details={
                "two_tailed": two_tailed,
                "n_a": len(group_a),
                "n_b": len(group_b),
                "method": "scipy",
            },
        )

    def _ttest_manual(
        self,
        group_a: list[float],
        group_b: list[float],
        two_tailed: bool = True,
    ) -> StatisticalResult:
        """Manual t-test calculation (Welch's t-test)."""
        mean_a = sum(group_a) / len(group_a)
        mean_b = sum(group_b) / len(group_b)

        var_a = sum((x - mean_a) ** 2 for x in group_a) / (len(group_a) - 1)
        var_b = sum((x - mean_b) ** 2 for x in group_b) / (len(group_b) - 1)

        se = math.sqrt(var_a / len(group_a) + var_b / len(group_b))
        if se == 0:
            return StatisticalResult(
                test_name="t-test",
                statistic=0.0,
                p_value=1.0,
                details={"error": "Zero standard error"},
            )

        t_stat = (mean_a - mean_b) / se

        # Welch-Satterthwaite degrees of freedom
        num = (var_a / len(group_a) + var_b / len(group_b)) ** 2
        den = (
            (var_a / len(group_a)) ** 2 / (len(group_a) - 1)
            + (var_b / len(group_b)) ** 2 / (len(group_b) - 1)
        )
        df = num / den if den > 0 else len(group_a) + len(group_b) - 2

        # Approximate p-value using t-distribution approximation
        p_value = self._t_distribution_p_value(abs(t_stat), df)

        return StatisticalResult(
            test_name="t-test",
            statistic=t_stat,
            p_value=p_value,
            significant=p_value < self.alpha,
            alpha=self.alpha,
            details={
                "two_tailed": two_tailed,
                "n_a": len(group_a),
                "n_b": len(group_b),
                "df": round(df, 2),
                "method": "manual_welch",
            },
        )

    def _t_distribution_p_value(self, t: float, df: float) -> float:
        """Approximate p-value from t-statistic using normal approximation.

        Args:
            t: Absolute t-statistic.
            df: Degrees of freedom.

        Returns:
            Approximate two-tailed p-value.
        """
        # For large df, t-distribution approaches normal
        # Use a simple approximation
        if df > 100:
            # Normal approximation
            z = t
            p = 2 * (1 - self._normal_cdf(z))
        else:
            # Adjusted approximation for small df
            z = t * (1 - 1 / (4 * df))
            p = 2 * (1 - self._normal_cdf(z))

        return max(0.0, min(1.0, p))

    def _normal_cdf(self, x: float) -> float:
        """Approximate the standard normal CDF.

        Args:
            x: Z-score.

        Returns:
            Cumulative probability.
        """
        # Abramowitz and Stegun approximation
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911

        sign = 1 if x >= 0 else -1
        x = abs(x)

        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2)

        if sign == 1:
            return y
        else:
            return 1.0 - y

    def _chi_square_p_value(self, chi2: float, df: int) -> float:
        """Approximate p-value for chi-square statistic.

        Args:
            chi2: Chi-square statistic.
            df: Degrees of freedom.

        Returns:
            Approximate p-value.
        """
        if df <= 0:
            return 1.0

        # Wilson-Hilferty transformation to normal
        z = (
            (chi2 / df) ** (1 / 3) - (1 - 2 / (9 * df))
        ) / math.sqrt(2 / (9 * df))

        p = 1 - self._normal_cdf(z)
        return max(0.0, min(1.0, p))
