"""Deterministic classification rules for failure diagnosis.

Provides rule-based evidence evaluation for classifying
run failures into categories.
"""

from __future__ import annotations

from typing import Any

from forge.core.schemas import FailureCategory, RunResult


class DiagnosisRule:
    """A single diagnostic rule.

    A rule evaluates evidence and returns a category with confidence.

    Attributes:
        name: Human-readable rule name.
        category: The failure category this rule detects.
        priority: Higher priority rules are evaluated first.
    """

    def __init__(
        self,
        name: str,
        category: FailureCategory,
        priority: int = 0,
    ):
        self.name = name
        self.category = category
        self.priority = priority

    def evaluate(self, result: RunResult) -> tuple[bool, float, list[str]]:
        """Evaluate this rule against a run result.

        Args:
            result: The run result to evaluate.

        Returns:
            Tuple of (matches, confidence, evidence).
        """
        raise NotImplementedError


class EnvironmentFailureRule(DiagnosisRule):
    """Detects environment failures."""

    def __init__(self):
        super().__init__(
            "Environment Failure",
            FailureCategory.ENVIRONMENT_FAILURE,
            priority=10,
        )

    def evaluate(self, result: RunResult) -> tuple[bool, float, list[str]]:
        evidence = []
        confidence = 0.0

        # Check for environment-related errors
        if result.error:
            error_lower = result.error.lower()
            if any(kw in error_lower for kw in ["docker", "sandbox", "container", "dependency", "install"]):
                evidence.append(f"Error mentions environment: {result.error[:100]}")
                confidence += 0.6

        # Check if verification couldn't run
        if result.verification:
            if not result.verification.public_tests_ran and not result.verification.hidden_tests_ran:
                evidence.append("No tests were executed — environment may have failed")
                confidence += 0.4

        # Check for infrastructure-related diagnosis
        if result.diagnosis and result.diagnosis.primary_category == FailureCategory.ENVIRONMENT_FAILURE:
            evidence.append("Already diagnosed as environment failure")
            confidence = 0.9

        matches = confidence >= 0.5
        return matches, min(1.0, confidence), evidence


class InvalidTaskRule(DiagnosisRule):
    """Detects invalid tasks."""

    def __init__(self):
        super().__init__(
            "Invalid Task",
            FailureCategory.INVALID_TASK,
            priority=9,
        )

    def evaluate(self, result: RunResult) -> tuple[bool, float, list[str]]:
        evidence = []
        confidence = 0.0

        # If reference solution doesn't pass, task may be invalid
        if result.verification:
            if result.verification.reference_solution_checked and not result.verification.reference_solution_passed:
                evidence.append("Reference solution does not pass — task may be invalid")
                confidence += 0.7

            # If initial defect is not detected, task setup may be wrong
            if result.verification.initial_defect_checked and not result.verification.initial_defect_detected:
                evidence.append("Initial defect not detected — task setup may be incorrect")
                confidence += 0.5

        matches = confidence >= 0.5
        return matches, min(1.0, confidence), evidence


class VerifierFailureRule(DiagnosisRule):
    """Detects verifier failures."""

    def __init__(self):
        super().__init__(
            "Verifier Failure",
            FailureCategory.VERIFIER_FAILURE,
            priority=8,
        )

    def evaluate(self, result: RunResult) -> tuple[bool, float, list[str]]:
        evidence = []
        confidence = 0.0

        if result.verification:
            # Verifier ran but had errors
            if result.verification.public_tests_error or result.verification.hidden_tests_error:
                evidence.append("Verifier encountered errors during execution")
                confidence += 0.5

            # Agent believes success and verification passes, but diagnosis says otherwise
            if result.agent_believes_success and result.verification.passed and not result.passed:
                evidence.append(
                    "Agent succeeded and verifier passed, but run marked as failed — verifier inconsistency"
                )
                confidence += 0.6

        matches = confidence >= 0.5
        return matches, min(1.0, confidence), evidence


class InfrastructureFailureRule(DiagnosisRule):
    """Detects infrastructure failures."""

    def __init__(self):
        super().__init__(
            "Infrastructure Failure",
            FailureCategory.INFRASTRUCTURE_FAILURE,
            priority=7,
        )

    def evaluate(self, result: RunResult) -> tuple[bool, float, list[str]]:
        evidence = []
        confidence = 0.0

        from forge.core.schemas import RunStatus

        # Timeout
        if result.status == RunStatus.TIMED_OUT:
            evidence.append("Run timed out")
            confidence += 0.8

        # Error mentions timeout or API issues
        if result.error:
            error_lower = result.error.lower()
            if any(kw in error_lower for kw in ["timeout", "api", "network", "connection", "rate limit"]):
                evidence.append(f"Error suggests infrastructure issue: {result.error[:100]}")
                confidence += 0.5

        matches = confidence >= 0.5
        return matches, min(1.0, confidence), evidence


class AgentFailureRule(DiagnosisRule):
    """Detects genuine agent failures (default when no other rule matches)."""

    def __init__(self):
        super().__init__(
            "Agent Failure",
            FailureCategory.AGENT_FAILURE,
            priority=1,
        )

    def evaluate(self, result: RunResult) -> tuple[bool, float, list[str]]:
        evidence = []
        confidence = 0.0

        # Agent didn't pass
        if not result.passed:
            confidence += 0.3

            # Agent made changes but still didn't pass
            if result.agent_made_changes:
                evidence.append("Agent made changes but did not solve the task")
                confidence += 0.3

            # Agent didn't make any changes
            if not result.agent_made_changes:
                evidence.append("Agent did not make any changes")
                confidence += 0.2

            # Verification ran and confirmed failure
            if result.verification and not result.verification.passed:
                evidence.append("Independent verification confirmed task not solved")
                confidence += 0.2

        matches = confidence >= 0.3
        return matches, min(1.0, confidence), evidence


def get_all_rules() -> list[DiagnosisRule]:
    """Return all diagnostic rules, sorted by priority.

    Returns:
        List of DiagnosisRule instances, highest priority first.
    """
    rules = [
        EnvironmentFailureRule(),
        InvalidTaskRule(),
        VerifierFailureRule(),
        InfrastructureFailureRule(),
        AgentFailureRule(),
    ]
    return sorted(rules, key=lambda r: r.priority, reverse=True)


def evaluate_rules(result: RunResult) -> list[dict[str, Any]]:
    """Evaluate all rules against a run result.

    Args:
        result: The run result to evaluate.

    Returns:
        List of rule evaluation results, sorted by confidence.
    """
    evaluations = []
    for rule in get_all_rules():
        matches, confidence, evidence = rule.evaluate(result)
        evaluations.append(
            {
                "rule": rule.name,
                "category": rule.category,
                "matches": matches,
                "confidence": confidence,
                "evidence": evidence,
            }
        )

    return sorted(evaluations, key=lambda e: e["confidence"], reverse=True)
