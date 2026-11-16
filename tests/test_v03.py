"""Tests for v0.3 features: data versioning, example curation, experiment runner, statistics."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Data Versioning
# ---------------------------------------------------------------------------


class TestDatasetVersioner:
    """Tests for forge/training/versioning.py"""

    def test_create_version(self, tmp_path: Path):
        """Create a versioned dataset."""
        from forge.training.versioning import DatasetVersioner

        versioner = DatasetVersioner(versions_dir=tmp_path / "versions")
        examples = [{"task_id": "task-1", "passed": True}, {"task_id": "task-2", "passed": False}]
        version = versioner.create_version("v1.0", examples, description="Test version")

        assert version.version_tag == "v1.0"
        assert version.num_examples == 2
        assert version.description == "Test version"
        assert (tmp_path / "versions" / "v1.0" / "data.jsonl").exists()
        assert (tmp_path / "versions" / "v1.0" / "manifest.json").exists()

    def test_list_versions(self, tmp_path: Path):
        """List all versions."""
        from forge.training.versioning import DatasetVersioner

        versioner = DatasetVersioner(versions_dir=tmp_path / "versions")
        versioner.create_version("v1.0", [{"a": 1}])
        versioner.create_version("v2.0", [{"b": 2}])

        versions = versioner.list_versions()
        assert len(versions) == 2
        assert versions[0].version_tag == "v1.0"
        assert versions[1].version_tag == "v2.0"

    def test_list_versions_empty(self, tmp_path: Path):
        """List versions when none exist."""
        from forge.training.versioning import DatasetVersioner

        versioner = DatasetVersioner(versions_dir=tmp_path / "versions")
        versions = versioner.list_versions()
        assert versions == []

    def test_load_version(self, tmp_path: Path):
        """Load examples from a version."""
        from forge.training.versioning import DatasetVersioner

        versioner = DatasetVersioner(versions_dir=tmp_path / "versions")
        examples = [{"task_id": "task-1"}, {"task_id": "task-2"}]
        versioner.create_version("v1.0", examples)

        loaded = versioner.load_version("v1.0")
        assert len(loaded) == 2
        assert loaded[0]["task_id"] == "task-1"

    def test_load_version_not_found(self, tmp_path: Path):
        """Loading nonexistent version raises FileNotFoundError."""
        from forge.training.versioning import DatasetVersioner

        versioner = DatasetVersioner(versions_dir=tmp_path / "versions")
        with pytest.raises(FileNotFoundError):
            versioner.load_version("nonexistent")

    def test_diff_versions(self, tmp_path: Path):
        """Diff two versions."""
        from forge.training.versioning import DatasetVersioner

        versioner = DatasetVersioner(versions_dir=tmp_path / "versions")
        versioner.create_version("v1.0", [{"a": 1}])
        versioner.create_version("v2.0", [{"a": 1}, {"b": 2}, {"c": 3}])

        diff = versioner.diff_versions("v1.0", "v2.0")
        assert diff["diff"]["example_count_diff"] == 2
        assert diff["diff"]["examples_added"] == 2
        assert diff["diff"]["examples_removed"] == 0

    def test_diff_versions_missing(self, tmp_path: Path):
        """Diff with missing version raises error."""
        from forge.training.versioning import DatasetVersioner

        versioner = DatasetVersioner(versions_dir=tmp_path / "versions")
        versioner.create_version("v1.0", [{"a": 1}])
        with pytest.raises(FileNotFoundError):
            versioner.diff_versions("v1.0", "missing")

    def test_version_serialization(self, tmp_path: Path):
        """Version to_dict and from_dict round-trip."""
        from forge.training.versioning import DatasetVersion

        v = DatasetVersion(version_tag="v1.0", created_at="2024-01-01", num_examples=5)
        data = v.to_dict()
        v2 = DatasetVersion.from_dict(data)
        assert v2.version_tag == v.version_tag
        assert v2.num_examples == v.num_examples


# ---------------------------------------------------------------------------
# Example Curator
# ---------------------------------------------------------------------------


class TestExampleCurator:
    """Tests for forge/training/curator.py"""

    def _make_result(self, passed: bool, failure_cat=None, reward: float = 0.0):
        from forge.core.schemas import (
            FailureCategory,
            FailureDiagnosis,
            RunResult,
            RunStatus,
            Trajectory,
            TrajectoryStep,
        )

        diagnosis = None
        if failure_cat:
            diagnosis = FailureDiagnosis(
                run_id="run-1",
                primary_category=FailureCategory(failure_cat),
                confidence=0.8,
            )

        traj = Trajectory(run_id="run-1", task_id="task-1", agent_id="mock")
        traj.add_step(TrajectoryStep(step_index=0, action="test"))
        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="mock",
            status=RunStatus.COMPLETED,
        )
        result.passed = passed
        result.trajectory = traj
        result.diagnosis = diagnosis
        result.metadata = {"agent_id": "mock", "reward": reward}
        return result

    def test_curate_positive(self):
        """Curate positive examples from passed runs."""
        from forge.training.curator import ExampleCurator

        results = [
            self._make_result(passed=True, reward=1.0),
            self._make_result(passed=False, failure_cat="agent_failure"),
        ]
        curator = ExampleCurator()
        positive = curator.curate_positive(results)

        assert len(positive) == 1
        assert positive[0].is_positive is True
        assert positive[0].passed is True

    def test_curate_positive_min_reward(self):
        """Filter by minimum reward."""
        from forge.training.curator import ExampleCurator

        results = [
            self._make_result(passed=True, reward=0.3),
            self._make_result(passed=True, reward=0.8),
        ]
        curator = ExampleCurator()
        positive = curator.curate_positive(results, min_reward=0.5)

        assert len(positive) == 1

    def test_curate_negative(self):
        """Curate negative examples from agent_failure runs."""
        from forge.training.curator import ExampleCurator

        results = [
            self._make_result(passed=True),
            self._make_result(passed=False, failure_cat="agent_failure"),
            self._make_result(passed=False, failure_cat="environment_failure"),
        ]
        curator = ExampleCurator()
        negative = curator.curate_negative(results)

        assert len(negative) == 1
        assert negative[0].is_positive is False
        assert negative[0].failure_category.value == "agent_failure"

    def test_curate_by_category(self):
        """Curate by specific failure category."""
        from forge.core.schemas import FailureCategory
        from forge.training.curator import ExampleCurator

        results = [
            self._make_result(passed=False, failure_cat="agent_failure"),
            self._make_result(passed=False, failure_cat="verifier_failure"),
        ]
        curator = ExampleCurator()
        examples = curator.curate_by_category(results, FailureCategory.VERIFIER_FAILURE)

        assert len(examples) == 1
        assert examples[0].failure_category == FailureCategory.VERIFIER_FAILURE

    def test_export_sft_format(self, tmp_path: Path):
        """Export in SFT format."""
        from forge.training.curator import CuratedExample, ExampleCurator

        examples = [
            CuratedExample(task_id="task-1", agent_id="mock", is_positive=True, passed=True),
        ]
        output = tmp_path / "sft.jsonl"
        curator = ExampleCurator()
        sft = curator.export_sft_format(examples, output)

        assert len(sft) == 1
        assert "messages" in sft[0]
        assert output.exists()

    def test_export_rl_format(self, tmp_path: Path):
        """Export in RL format."""
        from forge.training.curator import CuratedExample, ExampleCurator

        examples = [
            CuratedExample(task_id="task-1", agent_id="mock", is_positive=False, passed=False),
        ]
        output = tmp_path / "rl.jsonl"
        curator = ExampleCurator()
        rl = curator.export_rl_format(examples, output)

        assert len(rl) == 1
        assert "state" in rl[0]
        assert rl[0]["reward"] == -1.0
        assert output.exists()

    def test_curated_example_to_dict(self):
        """CuratedExample serialization."""
        from forge.core.schemas import FailureCategory
        from forge.training.curator import CuratedExample

        ex = CuratedExample(
            task_id="task-1",
            agent_id="mock",
            is_positive=False,
            passed=False,
            failure_category=FailureCategory.AGENT_FAILURE,
        )
        data = ex.to_dict()
        assert data["task_id"] == "task-1"
        assert data["failure_category"] == "agent_failure"


# ---------------------------------------------------------------------------
# Experiment Runner
# ---------------------------------------------------------------------------


class TestExperimentRunner:
    """Tests for forge/experiments/runner.py"""

    def test_run_experiment(self):
        """Run a single experiment."""
        from forge.experiments.manager import ExperimentConfig
        from forge.experiments.runner import ExperimentRunner

        config = ExperimentConfig(name="Test", hypothesis="Test hypothesis")
        runner = ExperimentRunner()
        result = runner.run_experiment(config, task_ids=["task-1", "task-2", "task-3"])

        assert result.experiment_id is not None
        assert result.total_runs == 3
        assert result.passed_runs == 3
        assert result.success_rate == 1.0

    def test_run_paired_experiment(self):
        """Run two experiments and compare."""
        from forge.experiments.manager import ExperimentConfig
        from forge.experiments.runner import ExperimentRunner

        config_a = ExperimentConfig(name="A", hypothesis="A hypothesis")
        config_b = ExperimentConfig(name="B", hypothesis="B hypothesis")
        runner = ExperimentRunner()
        comparison = runner.run_paired_experiment(
            config_a, config_b, task_ids=["task-1", "task-2"]
        )

        assert "experiment_a" in comparison
        assert "experiment_b" in comparison
        assert "comparison" in comparison

    def test_run_experiment_with_orchestrator(self):
        """Run experiment with custom orchestrator."""
        from forge.core.schemas import RunResult, RunStatus
        from forge.experiments.manager import ExperimentConfig
        from forge.experiments.runner import ExperimentRunner

        def custom_run(task_id, agent_type):
            result = RunResult(
                run_id=f"run-{task_id}",
                task_id=task_id,
                agent_id="mock",
                status=RunStatus.FAILED,
            )
            result.passed = False
            return result

        config = ExperimentConfig(name="Test", hypothesis="Test")
        runner = ExperimentRunner()
        result = runner.run_experiment(
            config,
            task_ids=["task-1"],
            orchestrator_run=custom_run,
        )

        assert result.passed_runs == 0
        assert result.failed_runs == 1

    def test_run_experiment_empty_tasks(self):
        """Run experiment with no tasks."""
        from forge.experiments.manager import ExperimentConfig
        from forge.experiments.runner import ExperimentRunner

        config = ExperimentConfig(name="Empty", hypothesis="Empty test")
        runner = ExperimentRunner()
        result = runner.run_experiment(config, task_ids=[])

        assert result.total_runs == 0


# ---------------------------------------------------------------------------
# Statistical Analyzer
# ---------------------------------------------------------------------------


class TestStatisticalAnalyzer:
    """Tests for forge/experiments/statistics.py"""

    def test_ttest(self):
        """T-test between two groups."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        result = analyzer.ttest([1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 3.0, 4.0, 5.0, 6.0])

        assert result.test_name == "t-test"
        assert result.statistic != 0 or result.p_value != 0

    def test_ttest_too_few_samples(self):
        """T-test with insufficient samples."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        result = analyzer.ttest([1.0], [2.0, 3.0])
        assert "error" in result.details

    def test_effect_size(self):
        """Cohen's d effect size."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        result = analyzer.effect_size([1.0, 1.0, 1.0], [5.0, 5.0, 5.0])

        assert result.test_name == "cohens_d"
        assert abs(result.statistic) > 1.0  # Large effect
        assert result.details["interpretation"] == "large"

    def test_effect_size_negligible(self):
        """Negligible effect size."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        result = analyzer.effect_size([1.0, 1.1, 1.0], [1.0, 1.0, 1.1])
        assert result.details["interpretation"] in ("negligible", "small")

    def test_confidence_interval(self):
        """Confidence interval for mean."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        result = analyzer.confidence_interval([1.0, 2.0, 3.0, 4.0, 5.0])

        assert result.statistic == 3.0  # Mean
        assert "ci_lower" in result.details
        assert "ci_upper" in result.details
        assert result.details["ci_lower"] < 3.0 < result.details["ci_upper"]

    def test_confidence_interval_empty(self):
        """Confidence interval with no values."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        result = analyzer.confidence_interval([])
        assert "error" in result.details

    def test_chi_square(self):
        """Chi-square goodness-of-fit test."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        result = analyzer.chi_square([10, 20, 30], [20, 20, 20])

        assert result.test_name == "chi_square"
        assert result.statistic > 0

    def test_chi_square_empty(self):
        """Chi-square with no observed values."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        result = analyzer.chi_square([])
        assert "error" in result.details

    def test_generate_report(self):
        """Generate full statistical report."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        report = analyzer.generate_report(
            [1.0, 1.0, 0.5, 0.5, 1.0],
            [0.5, 0.5, 0.5, 0.0, 0.5],
            name_a="Method A",
            name_b="Method B",
        )

        assert "groups" in report
        assert "tests" in report
        assert "summary" in report
        assert "Method A" in report["groups"]

    def test_statistical_result_to_dict(self):
        """StatisticalResult serialization."""
        from forge.experiments.statistics import StatisticalResult

        result = StatisticalResult(
            test_name="t-test",
            statistic=2.5,
            p_value=0.01,
            significant=True,
        )
        data = result.to_dict()
        assert data["test_name"] == "t-test"
        assert data["significant"] is True

    def test_normal_cdf(self):
        """Normal CDF approximation."""
        from forge.experiments.statistics import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        # CDF at large positive should be ~1.0
        cdf_large = analyzer._normal_cdf(5.0)
        assert cdf_large > 0.99
        # CDF at large negative should be ~0.0
        cdf_neg = analyzer._normal_cdf(-5.0)
        assert cdf_neg < 0.01

    def test_generate_summary(self):
        """Summary generation."""
        from forge.experiments.statistics import StatisticalAnalyzer, StatisticalResult

        analyzer = StatisticalAnalyzer()
        ttest_result = StatisticalResult(
            test_name="t-test", statistic=2.5, p_value=0.01, significant=True
        )
        effect_result = StatisticalResult(
            test_name="cohens_d", statistic=0.8, details={"interpretation": "medium"}
        )
        summary = analyzer._generate_summary(ttest_result, effect_result)
        assert "Statistical Analysis Summary" in summary
        assert "significant" in summary.lower()
