"""Evidence collection and confidence scoring for diagnosis.

Collects evidence from run results and computes confidence scores
for each failure category.
"""

from __future__ import annotations

from typing import Any

from forge.core.schemas import FailureCategory, RunResult
from forge.diagnosis.rules import evaluate_rules


class EvidenceCollector:
    """Collects and aggregates evidence for failure diagnosis.

    Gathers evidence from multiple sources (run result, verification,
    trajectory, rules) and computes confidence scores.
    """

    def __init__(self):
        self.supporting: dict[FailureCategory, list[str]] = {cat: [] for cat in FailureCategory}
        self.contradictory: dict[FailureCategory, list[str]] = {cat: [] for cat in FailureCategory}
        self.confidence: dict[FailureCategory, float] = {cat: 0.0 for cat in FailureCategory}

    def collect_from_result(self, result: RunResult) -> EvidenceCollector:
        """Collect evidence from a run result.

        Args:
            result: The run result to analyze.

        Returns:
            Self for chaining.
        """
        # Run-level evidence
        if result.passed:
            self.supporting[FailureCategory.AGENT_FAILURE].append("Task was passed — not a failure")
            self.confidence[FailureCategory.AGENT_FAILURE] = 0.0
            return self

        # Error evidence
        if result.error:
            error_lower = result.error.lower()
            if any(kw in error_lower for kw in ["docker", "sandbox", "container"]):
                self.supporting[FailureCategory.ENVIRONMENT_FAILURE].append(
                    f"Error mentions sandbox: {result.error[:80]}"
                )
                self.confidence[FailureCategory.ENVIRONMENT_FAILURE] += 0.3
            if any(kw in error_lower for kw in ["timeout", "timed out"]):
                self.supporting[FailureCategory.INFRASTRUCTURE_FAILURE].append("Run timed out")
                self.confidence[FailureCategory.INFRASTRUCTURE_FAILURE] += 0.5

        # Verification evidence
        if result.verification:
            v = result.verification
            if not v.public_tests_ran and not v.hidden_tests_ran:
                self.supporting[FailureCategory.ENVIRONMENT_FAILURE].append(
                    "No tests executed — environment likely failed"
                )
                self.confidence[FailureCategory.ENVIRONMENT_FAILURE] += 0.3

            if v.reference_solution_checked and not v.reference_solution_passed:
                self.supporting[FailureCategory.INVALID_TASK].append("Reference solution does not pass")
                self.confidence[FailureCategory.INVALID_TASK] += 0.5

            if v.public_tests_error or v.hidden_tests_error:
                self.supporting[FailureCategory.VERIFIER_FAILURE].append("Verifier encountered errors")
                self.confidence[FailureCategory.VERIFIER_FAILURE] += 0.3

        # Agent behavior evidence
        if not result.agent_made_changes and not result.passed:
            self.supporting[FailureCategory.AGENT_FAILURE].append("Agent made no changes")
            self.confidence[FailureCategory.AGENT_FAILURE] += 0.2

        return self

    def collect_from_rules(self, result: RunResult) -> EvidenceCollector:
        """Collect evidence from diagnostic rules.

        Args:
            result: The run result to evaluate.

        Returns:
            Self for chaining.
        """
        evaluations = evaluate_rules(result)
        for eval_result in evaluations:
            category = eval_result["category"]
            if isinstance(category, str):
                try:
                    category = FailureCategory(category)
                except ValueError:
                    continue

            if eval_result["matches"]:
                for evidence in eval_result["evidence"]:
                    if evidence not in self.supporting[category]:
                        self.supporting[category].append(evidence)
                self.confidence[category] = max(
                    self.confidence[category],
                    eval_result["confidence"],
                )
            else:
                # Non-matching rules provide contradictory evidence
                if eval_result["confidence"] > 0.3:
                    self.contradictory[category].append(f"Rule '{eval_result['rule']}' did not match")

        return self

    def get_primary_category(self) -> tuple[FailureCategory, float]:
        """Get the primary failure category with highest confidence.

        Returns:
            Tuple of (category, confidence).
        """
        best_category = FailureCategory.UNCERTAIN
        best_confidence = 0.0

        for category, confidence in self.confidence.items():
            if confidence > best_confidence:
                best_confidence = confidence
                best_category = category

        # If no category has meaningful confidence, return uncertain
        if best_confidence < 0.3:
            return FailureCategory.UNCERTAIN, 0.5

        return best_category, min(1.0, best_confidence)

    def to_dict(self) -> dict[str, Any]:
        """Export collected evidence as a dictionary.

        Returns:
            Dictionary with all evidence and confidence scores.
        """
        return {
            "supporting": {cat.value: evidence for cat, evidence in self.supporting.items() if evidence},
            "contradictory": {cat.value: evidence for cat, evidence in self.contradictory.items() if evidence},
            "confidence": {cat.value: round(conf, 4) for cat, conf in self.confidence.items()},
        }


def triage_run(result: RunResult) -> dict[str, Any]:
    """Perform full triage on a run result.

    Collects evidence from all sources and determines the primary
    failure category.

    Args:
        result: The run result to triage.

    Returns:
        Dictionary with triage results.
    """
    collector = EvidenceCollector()
    collector.collect_from_result(result)
    collector.collect_from_rules(result)

    category, confidence = collector.get_primary_category()

    return {
        "primary_category": category.value,
        "confidence": round(confidence, 4),
        "evidence": collector.to_dict(),
    }
