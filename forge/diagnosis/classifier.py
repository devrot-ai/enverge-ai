"""Failure attribution engine for ForgeLab.

This module classifies the cause of a failed agent run into one of six
categories using deterministic rules and evidence collection.  The goal
is to never automatically blame the agent — first establish that the
environment, task, and verifier were valid.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from forge.core.schemas import FailureCategory, RunResult, RunStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------


@dataclass
class EvidenceItem:
    """A single piece of evidence supporting or contradicting a diagnosis."""

    category: FailureCategory
    description: str
    is_supporting: bool  # True = supports this category, False = contradicts
    confidence_weight: float = 1.0  # How much this evidence weighs (0.0-1.0)


@dataclass
class FailureDiagnosis:
    """Complete diagnosis of a failed run.

    Attributes:
        run_id: The run being diagnosed.
        primary_category: Most likely cause of failure.
        supporting_evidence: Evidence supporting the primary diagnosis.
        contradictory_evidence: Evidence contradicting the primary diagnosis.
        confidence: Confidence score 0.0-1.0.
        affected_component: Which component is suspected to be at fault.
        recommended_action: Suggested next step.
        diagnosis_version: Version of the diagnosis schema.
        all_evidence: All collected evidence items.
        alternative_categories: Other categories considered with scores.
    """

    run_id: str
    primary_category: FailureCategory
    supporting_evidence: list[str] = field(default_factory=list)
    contradictory_evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    affected_component: str = ""
    recommended_action: str = ""
    diagnosis_version: str = "1.0"
    all_evidence: list[EvidenceItem] = field(default_factory=list)
    alternative_categories: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "primary_category": self.primary_category.value,
            "supporting_evidence": self.supporting_evidence,
            "contradictory_evidence": self.contradictory_evidence,
            "confidence": self.confidence,
            "affected_component": self.affected_component,
            "recommended_action": self.recommended_action,
            "diagnosis_version": self.diagnosis_version,
            "alternative_categories": self.alternative_categories,
        }


# ---------------------------------------------------------------------------
# Deterministic rules
# ---------------------------------------------------------------------------


class DiagnosisRules:
    """Deterministic rules for classifying run failures.

    Each rule examines the run result and verification output to collect
    evidence for or against each failure category.
    """

    @staticmethod
    def check_environment_failure(run_result: RunResult) -> list[EvidenceItem]:
        """Check for signs of environment setup or execution failure."""
        evidence: list[EvidenceItem] = []

        # Check if the run had infrastructure errors
        status_val = run_result.status.value if isinstance(run_result.status, RunStatus) else run_result.status
        if status_val in ("failed", "timed_out"):
            if run_result.error and any(
                kw in run_result.error.lower()
                for kw in ["dependency", "install", "import", "module not found", "no module"]
            ):
                evidence.append(
                    EvidenceItem(
                        category=FailureCategory.ENVIRONMENT_FAILURE,
                        description=f"Dependency/installation error: {run_result.error[:200]}",
                        is_supporting=True,
                        confidence_weight=0.9,
                    )
                )

        # Check if public tests could even run
        if run_result.verification:
            ver = run_result.verification
            if not ver.public_tests_ran:
                evidence.append(
                    EvidenceItem(
                        category=FailureCategory.ENVIRONMENT_FAILURE,
                        description="Public tests could not execute — environment may be broken",
                        is_supporting=True,
                        confidence_weight=0.85,
                    )
                )
            if ver.public_tests_error:
                evidence.append(
                    EvidenceItem(
                        category=FailureCategory.ENVIRONMENT_FAILURE,
                        description=f"Public test execution error: {ver.public_tests_error[:200]}",
                        is_supporting=True,
                        confidence_weight=0.8,
                    )
                )

        # Check for sandbox errors
        if run_result.error and any(
            kw in run_result.error.lower() for kw in ["sandbox", "container", "docker", "permission denied", "timeout"]
        ):
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.ENVIRONMENT_FAILURE,
                    description=f"Sandbox/container error: {run_result.error[:200]}",
                    is_supporting=True,
                    confidence_weight=0.9,
                )
            )

        return evidence

    @staticmethod
    def check_verifier_failure(run_result: RunResult) -> list[EvidenceItem]:
        """Check for signs that the verifier itself is defective."""
        evidence: list[EvidenceItem] = []

        if not run_result.verification:
            return evidence

        ver = run_result.verification

        # Reference solution should always pass — if it doesn't, verifier is broken
        if ver.reference_solution_checked and not ver.reference_solution_passed:
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.VERIFIER_FAILURE,
                    description="Reference solution failed hidden tests — verifier or hidden tests are broken",
                    is_supporting=True,
                    confidence_weight=0.95,
                )
            )

        # Hidden tests error
        if ver.hidden_tests_error:
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.VERIFIER_FAILURE,
                    description=f"Hidden test execution error: {ver.hidden_tests_error[:200]}",
                    is_supporting=True,
                    confidence_weight=0.85,
                )
            )

        # Inconsistent results: agent passed public but failed hidden with no code change
        if ver.public_tests_passed and not ver.hidden_tests_passed:
            if run_result.agent_made_changes:
                # Agent changed code — this is normal, not a verifier failure
                evidence.append(
                    EvidenceItem(
                        category=FailureCategory.VERIFIER_FAILURE,
                        description="Agent passed public tests but failed hidden tests after making changes",
                        is_supporting=False,  # This is expected behavior, not a verifier failure
                        confidence_weight=0.3,
                    )
                )
            else:
                # Agent didn't change anything but public passed and hidden failed — initial defect check
                pass

        return evidence

    @staticmethod
    def check_invalid_task(run_result: RunResult) -> list[EvidenceItem]:
        """Check for signs that the task specification is invalid."""
        evidence: list[EvidenceItem] = []

        if not run_result.verification:
            return evidence

        ver = run_result.verification

        # If initial defect check passed (defect was NOT detected), task may be invalid
        if ver.initial_defect_checked and not ver.initial_defect_detected:
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.INVALID_TASK,
                    description="Initial defect not detected — task may not have the intended bug",
                    is_supporting=True,
                    confidence_weight=0.8,
                )
            )

        # If reference solution doesn't pass, task might be impossible
        if ver.reference_solution_checked and not ver.reference_solution_passed:
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.INVALID_TASK,
                    description="Reference solution doesn't pass — task may be unsolvable or mis-specified",
                    is_supporting=True,
                    confidence_weight=0.7,
                )
            )

        # Task metadata indicates issues
        if run_result.metadata:
            task_info = run_result.metadata.get("task_validation", {})
            if task_info.get("ambiguous"):
                evidence.append(
                    EvidenceItem(
                        category=FailureCategory.INVALID_TASK,
                        description="Task marked as ambiguous during validation",
                        is_supporting=True,
                        confidence_weight=0.6,
                    )
                )

        return evidence

    @staticmethod
    def check_infrastructure_failure(run_result: RunResult) -> list[EvidenceItem]:
        """Check for signs of infrastructure-level failures."""
        evidence: list[EvidenceItem] = []

        status_val = run_result.status.value if isinstance(run_result.status, RunStatus) else run_result.status
        if status_val == "timed_out":
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.INFRASTRUCTURE_FAILURE,
                    description=f"Run timed out after {run_result.duration_seconds:.0f}s",
                    is_supporting=True,
                    confidence_weight=0.7,
                )
            )

        if run_result.error and any(
            kw in run_result.error.lower()
            for kw in ["connection refused", "api error", "rate limit", "network", "disk full"]
        ):
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.INFRASTRUCTURE_FAILURE,
                    description=f"Infrastructure error: {run_result.error[:200]}",
                    is_supporting=True,
                    confidence_weight=0.85,
                )
            )

        # Agent didn't make any progress at all (0 steps)
        if run_result.step_count == 0 and status_val == "failed":
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.INFRASTRUCTURE_FAILURE,
                    description="Agent executed 0 steps — run may have failed to initialize",
                    is_supporting=True,
                    confidence_weight=0.6,
                )
            )

        return evidence

    @staticmethod
    def check_agent_failure(run_result: RunResult) -> list[EvidenceItem]:
        """Check for signs of genuine agent capability failure.

        This is the default category when all other checks pass:
        the environment is valid, the task is solvable, the verifier works,
        but the agent couldn't solve it.
        """
        evidence: list[EvidenceItem] = []

        if not run_result.verification:
            return evidence

        ver = run_result.verification

        # Agent made changes but didn't pass hidden tests
        if run_result.agent_made_changes and ver.hidden_tests_ran and not ver.hidden_tests_passed:
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.AGENT_FAILURE,
                    description="Agent made code changes but solution didn't pass hidden tests",
                    is_supporting=True,
                    confidence_weight=0.75,
                )
            )

        # Agent didn't make any changes
        if not run_result.agent_made_changes and ver.initial_defect_detected:
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.AGENT_FAILURE,
                    description="Agent made no code changes — didn't attempt to fix the bug",
                    is_supporting=True,
                    confidence_weight=0.8,
                )
            )

        # Agent ran out of steps
        if run_result.step_count >= (run_result.metadata or {}).get("max_steps", 999):
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.AGENT_FAILURE,
                    description=f"Agent exhausted {run_result.step_count} steps without solving task",
                    is_supporting=True,
                    confidence_weight=0.6,
                )
            )

        # Agent's self-assessment was wrong
        if run_result.agent_believes_success and not ver.hidden_tests_passed:
            evidence.append(
                EvidenceItem(
                    category=FailureCategory.AGENT_FAILURE,
                    description="Agent claimed success but solution failed verification",
                    is_supporting=True,
                    confidence_weight=0.7,
                )
            )

        return evidence


# ---------------------------------------------------------------------------
# Triage / classifier
# ---------------------------------------------------------------------------


class FailureClassifier:
    """Classifies run failures by collecting evidence and scoring categories.

    Usage:
        classifier = FailureClassifier()
        diagnosis = classifier.classify(run_result)
    """

    def __init__(self, uncertain_threshold: float = 0.3):
        self.rules = DiagnosisRules()
        self.uncertain_threshold = uncertain_threshold

    def classify(self, run_result: RunResult) -> FailureDiagnosis:
        """Classify a run result into a failure category.

        Args:
            run_result: The completed run with verification results.

        Returns:
            A FailureDiagnosis with the primary category and evidence.
        """
        # If the run succeeded, no diagnosis needed
        status_val = run_result.status.value if isinstance(run_result.status, RunStatus) else run_result.status
        if status_val == "completed" and run_result.passed:
            return FailureDiagnosis(
                run_id=run_result.run_id,
                primary_category=FailureCategory.AGENT_FAILURE,  # placeholder — success
                supporting_evidence=["Run completed successfully"],
                confidence=1.0,
                recommended_action="None — run was successful",
            )

        # Collect all evidence
        all_evidence: list[EvidenceItem] = []
        all_evidence.extend(self.rules.check_environment_failure(run_result))
        all_evidence.extend(self.rules.check_verifier_failure(run_result))
        all_evidence.extend(self.rules.check_invalid_task(run_result))
        all_evidence.extend(self.rules.check_infrastructure_failure(run_result))
        all_evidence.extend(self.rules.check_agent_failure(run_result))

        # Score each category
        category_scores = self._score_categories(all_evidence)

        # Determine primary category
        primary, confidence = self._select_primary(category_scores)

        # Build diagnosis
        supporting = [e.description for e in all_evidence if e.category == primary and e.is_supporting]
        contradictory = [e.description for e in all_evidence if e.category == primary and not e.is_supporting]

        # Check for contradictory evidence from other categories
        for cat, score in category_scores.items():
            if cat != primary and score > 0.5:
                contradictory.append(f"Alternative category {cat.value} scored {score:.2f}")

        # Determine affected component and recommended action
        affected, action = self._recommend_action(primary, run_result)

        # Build alternatives dict (exclude primary)
        alternatives = {cat.value: score for cat, score in category_scores.items() if cat != primary}

        return FailureDiagnosis(
            run_id=run_result.run_id,
            primary_category=primary,
            supporting_evidence=supporting,
            contradictory_evidence=contradictory,
            confidence=confidence,
            affected_component=affected,
            recommended_action=action,
            all_evidence=all_evidence,
            alternative_categories=alternatives,
        )

    def _score_categories(self, evidence: list[EvidenceItem]) -> dict[FailureCategory, float]:
        """Score each failure category based on collected evidence."""
        scores: dict[FailureCategory, float] = {
            FailureCategory.AGENT_FAILURE: 0.0,
            FailureCategory.ENVIRONMENT_FAILURE: 0.0,
            FailureCategory.INVALID_TASK: 0.0,
            FailureCategory.VERIFIER_FAILURE: 0.0,
            FailureCategory.INFRASTRUCTURE_FAILURE: 0.0,
            FailureCategory.UNCERTAIN: 0.0,
        }

        for item in evidence:
            if item.is_supporting:
                scores[item.category] = max(scores[item.category], item.confidence_weight)
            else:
                # Contradictory evidence reduces the score
                scores[item.category] = min(
                    scores[item.category],
                    max(0.0, 1.0 - item.confidence_weight),
                )

        return scores

    def _select_primary(self, scores: dict[FailureCategory, float]) -> tuple[FailureCategory, float]:
        """Select the primary failure category and confidence.

        If the highest score is below the uncertain threshold, return UNCERTAIN.
        If verifier or environment failure is detected with high confidence,
        prioritize those over agent failure.
        """
        # Priority order for high-confidence non-agent failures
        priority_order = [
            FailureCategory.VERIFIER_FAILURE,
            FailureCategory.ENVIRONMENT_FAILURE,
            FailureCategory.INVALID_TASK,
            FailureCategory.INFRASTRUCTURE_FAILURE,
            FailureCategory.AGENT_FAILURE,
        ]

        # Check for high-priority categories first
        for cat in priority_order:
            if scores[cat] >= 0.7:
                return cat, scores[cat]

        # Otherwise pick the highest score
        max_cat = max(scores, key=scores.get)
        max_score = scores[max_cat]

        if max_score < self.uncertain_threshold:
            return FailureCategory.UNCERTAIN, max_score

        return max_cat, max_score

    @staticmethod
    def _recommend_action(category: FailureCategory, run_result: RunResult) -> tuple[str, str]:
        """Return affected component and recommended action for a category."""
        actions = {
            FailureCategory.AGENT_FAILURE: (
                "agent",
                "Preserve as learning signal; generate targeted tasks for this weakness",
            ),
            FailureCategory.ENVIRONMENT_FAILURE: (
                "environment",
                "Quarantine world, repair environment template, revalidate",
            ),
            FailureCategory.INVALID_TASK: (
                "task",
                "Reject or revise task specification, revalidate before retry",
            ),
            FailureCategory.VERIFIER_FAILURE: (
                "verifier",
                "Repair hidden tests or verifier logic, rerun affected tasks",
            ),
            FailureCategory.INFRASTRUCTURE_FAILURE: (
                "infrastructure",
                "Check Docker, API connectivity, and resource limits; retry run",
            ),
            FailureCategory.UNCERTAIN: (
                "unknown",
                "Manual review required; insufficient evidence for automated diagnosis",
            ),
        }
        return actions.get(category, ("unknown", "Manual review required"))
