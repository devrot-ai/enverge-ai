"""Diagnosis module — failure attribution engine.

Provides evidence-based classification of run failures into 6 categories:
agent_failure, environment_failure, invalid_task, verifier_failure,
infrastructure_failure, and uncertain.
"""

__version__ = "0.1.0"

from forge.diagnosis.classifier import FailureClassifier
from forge.diagnosis.report import (
    batch_diagnose,
    create_diagnosis_report,
    format_diagnosis_summary,
    summarize_diagnoses,
)
from forge.diagnosis.rules import DiagnosisRule, evaluate_rules, get_all_rules
from forge.diagnosis.triage import EvidenceCollector, triage_run

__all__ = [
    "FailureClassifier",
    "DiagnosisRule",
    "get_all_rules",
    "evaluate_rules",
    "EvidenceCollector",
    "triage_run",
    "create_diagnosis_report",
    "format_diagnosis_summary",
    "batch_diagnose",
    "summarize_diagnoses",
]
