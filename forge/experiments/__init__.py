"""Experiments module — experiment management, execution, and analysis.

Provides:
- Experiment lifecycle management
- 7 preset experiments (A-D + ablation, difficulty, cross-template)
- End-to-end experiment runner
- Statistical analysis (t-tests, effect sizes, confidence intervals)
- Cross-experiment comparison
- Experiment configuration presets
- Artifact storage and retrieval
"""

__version__ = "0.1.0"

from forge.experiments.artifacts import ArtifactManager
from forge.experiments.comparison import compare_experiments, compare_failure_distributions, generate_comparison_report
from forge.experiments.config import get_preset_experiments
from forge.experiments.manager import ExperimentManager
from forge.experiments.runner import ExperimentResult, ExperimentRunner
from forge.experiments.statistics import StatisticalAnalyzer, StatisticalResult
from forge.experiments.ab_test import ABTestRunner, ABTestReport, ABTestResult
from forge.experiments.custom import CustomExperiment, CustomExperimentLoader
from forge.experiments.mlflow import MLflowTracker, MLflowRunResult

__all__ = [
    "ExperimentManager",
    "ExperimentRunner",
    "ExperimentResult",
    "StatisticalAnalyzer",
    "StatisticalResult",
    "get_preset_experiments",
    "compare_experiments",
    "compare_failure_distributions",
    "generate_comparison_report",
    "ArtifactManager",
    "ABTestRunner",
    "ABTestReport",
    "ABTestResult",
    "CustomExperiment",
    "CustomExperimentLoader",
    "MLflowTracker",
    "MLflowRunResult",
]
