"""Evaluation module — independent verification and metrics.

Provides:
- Verifier for running hidden tests in isolated containers
- Metrics computation (success rate, pass@k, verifier quality)
- Run scoring and evaluation reports
- JSON/Markdown report export
- Mutation coverage analysis
- Difficulty calibration
- Agent behavior analysis
- Report templates for different audiences
"""

__version__ = "0.1.0"

from forge.evaluation.behavior_analysis import (
    BehaviorAnalyzer,
    BehaviorProfile,
    FailureMode,
    ToolPattern,
)
from forge.evaluation.difficulty_calibration import CalibrationResult, DifficultyCalibrator
from forge.evaluation.metrics import (
    compute_average_duration,
    compute_failure_distribution,
    compute_metrics_summary,
    compute_pass_at_k,
    compute_success_rate,
    compute_verifier_quality,
)
from forge.evaluation.mutation_coverage import MutationCoverageAnalyzer, MutationCoverageReport
from forge.evaluation.reports import (
    export_report_json,
    export_report_markdown,
    format_report_summary,
    generate_run_summary,
)
from forge.evaluation.report_templates import ReportTemplate
from forge.evaluation.scoring import EvaluationReport, generate_evaluation_report, score_run, score_task_results
from forge.evaluation.verifier import Verifier

__all__ = [
    "Verifier",
    "compute_success_rate",
    "compute_pass_at_k",
    "compute_verifier_quality",
    "compute_failure_distribution",
    "compute_average_duration",
    "compute_metrics_summary",
    "score_run",
    "score_task_results",
    "generate_evaluation_report",
    "EvaluationReport",
    "format_report_summary",
    "export_report_json",
    "export_report_markdown",
    "generate_run_summary",
    "MutationCoverageAnalyzer",
    "MutationCoverageReport",
    "DifficultyCalibrator",
    "CalibrationResult",
    "BehaviorAnalyzer",
    "BehaviorProfile",
    "ToolPattern",
    "FailureMode",
    "ReportTemplate",
]
