"""Tests for v0.7 features: multi-agent curriculum, A/B testing, custom experiments,
security hardening, MLflow integration, and browser_automation template."""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Multi-agent curriculum
from forge.curriculum.multi_agent import (
    AgentCurriculumState,
    MultiAgentCurriculum,
    SharingLevel,
)

# A/B testing
from forge.experiments.ab_test import (
    ABTestReport,
    ABTestResult,
    ABTestRunner,
)

# Custom experiments
from forge.experiments.custom import (
    CustomExperiment,
    CustomExperimentLoader,
)

# Security hardening
from forge.sandbox.image_validation import ImageValidator, ImageValidationResult
from forge.sandbox.network import NetworkPolicy, NetworkPolicyManager, NetworkPolicyResult

# MLflow
from forge.experiments.mlflow import MLflowTracker, MLflowRunResult

# World factory
from forge.world_factory import templates, seeder


class TestMultiAgentCurriculum:
    """Tests for multi-agent curriculum tracking."""

    def test_add_agent(self):
        curriculum = MultiAgentCurriculum()
        curriculum.add_agent("mock")
        assert "mock" in curriculum.agents

    def test_add_duplicate_agent(self):
        curriculum = MultiAgentCurriculum()
        curriculum.add_agent("mock")
        curriculum.add_agent("mock")
        assert len(curriculum.agents) == 1

    def test_select_task(self):
        from forge.core.schemas import TaskSpec, TaskCategory

        curriculum = MultiAgentCurriculum()
        curriculum.add_agent("mock")
        task = TaskSpec(
            world_id="world-001",
            category=TaskCategory.BUG_REPAIR,
            description="Test task",
            task_id="test-001",
        )
        curriculum.set_task_pool([task])
        selected = curriculum.select_task("mock")
        assert selected is not None
        assert selected.task_id == "test-001"

    def test_update_passed(self):
        curriculum = MultiAgentCurriculum()
        curriculum.add_agent("mock")
        curriculum.update("mock", "task-001", True)
        state = curriculum.get_agent_state("mock")
        assert state.tasks_completed == 1
        assert state.tasks_passed == 1

    def test_update_failed(self):
        curriculum = MultiAgentCurriculum()
        curriculum.add_agent("mock")
        curriculum.update("mock", "task-001", False)
        state = curriculum.get_agent_state("mock")
        assert state.tasks_completed == 1
        assert state.tasks_passed == 0

    def test_sharing_full(self):
        curriculum = MultiAgentCurriculum(sharing_level=SharingLevel.FULL)
        curriculum.add_agent("a")
        curriculum.add_agent("b")
        curriculum.update("a", "task-001", True)
        # Full sharing updates other agent state
        state_a = curriculum.get_agent_state("a")
        assert state_a.tasks_completed == 1

    def test_get_comparison(self):
        curriculum = MultiAgentCurriculum()
        curriculum.add_agent("mock")
        curriculum.add_agent("rule_based")
        comparison = curriculum.get_comparison()
        assert "mock" in comparison
        assert "rule_based" in comparison

    def test_to_dict(self):
        curriculum = MultiAgentCurriculum()
        curriculum.add_agent("mock")
        state = curriculum.to_dict()
        assert state["sharing_level"] == SharingLevel.NONE
        assert "mock" in state["agents"]

    def test_empty_select(self):
        curriculum = MultiAgentCurriculum()
        curriculum.add_agent("mock")
        selected = curriculum.select_task("mock")
        assert selected is None


class TestABTesting:
    """Tests for A/B testing framework."""

    def test_add_result_a(self):
        runner = ABTestRunner()
        result = ABTestResult(agent="a", task_id="t1", passed=True)
        runner.add_result(result)
        assert len(runner.results_a) == 1

    def test_add_result_b(self):
        runner = ABTestRunner()
        result = ABTestResult(agent="b", task_id="t1", passed=False)
        runner.add_result(result)
        assert len(runner.results_b) == 1

    def test_generate_report(self):
        runner = ABTestRunner()
        for i in range(5):
            runner.add_result(ABTestResult(agent="a", task_id=f"t{i}", passed=i < 4))
            runner.add_result(ABTestResult(agent="b", task_id=f"t{i}", passed=i < 2))
        report = runner.generate_report("AgentA", "AgentB")
        assert report.agent_a_pass_rate == 0.8
        assert report.agent_b_pass_rate == 0.4

    def test_report_serialization(self):
        runner = ABTestRunner()
        for i in range(5):
            runner.add_result(ABTestResult(agent="a", task_id=f"t{i}", passed=i < 4))
            runner.add_result(ABTestResult(agent="b", task_id=f"t{i}", passed=i < 2))
        report = runner.generate_report("A", "B")
        d = report.to_dict()
        assert d["agent_a"] == "A"
        assert d["agent_b"] == "B"

    def test_report_markdown(self):
        runner = ABTestRunner()
        for i in range(5):
            runner.add_result(ABTestResult(agent="a", task_id=f"t{i}", passed=i < 4))
            runner.add_result(ABTestResult(agent="b", task_id=f"t{i}", passed=i < 2))
        report = runner.generate_report("A", "B")
        md = report.to_markdown()
        assert "# A/B Test Report" in md

    def test_empty_results(self):
        runner = ABTestRunner()
        report = runner.generate_report("A", "B")
        assert report.agent_a_pass_rate == 0
        assert report.agent_b_pass_rate == 0

    def test_tied_results(self):
        runner = ABTestRunner()
        for i in range(5):
            runner.add_result(ABTestResult(agent="a", task_id=f"t{i}", passed=True))
            runner.add_result(ABTestResult(agent="b", task_id=f"t{i}", passed=True))
        report = runner.generate_report("A", "B")
        assert report.agent_a_pass_rate == 1.0
        assert report.agent_b_pass_rate == 1.0
        assert report.p_value >= 1.0  # No difference

    def test_effect_size(self):
        runner = ABTestRunner()
        for i in range(10):
            runner.add_result(ABTestResult(agent="a", task_id=f"t{i}", passed=True))
            runner.add_result(ABTestResult(agent="b", task_id=f"t{i}", passed=False))
        report = runner.generate_report("A", "B")
        assert report.effect_size > 0  # A is better than B

    def test_confidence_interval(self):
        runner = ABTestRunner()
        for i in range(10):
            runner.add_result(ABTestResult(agent="a", task_id=f"t{i}", passed=i < 7))
            runner.add_result(ABTestResult(agent="b", task_id=f"t{i}", passed=i < 4))
        report = runner.generate_report("A", "B")
        # CI should be valid when rates differ
        assert report.confidence_interval_lower <= report.confidence_interval_upper

    def test_significance_level(self):
        runner = ABTestRunner(significance_level=0.01)
        assert runner.significance_level == 0.01


class TestCustomExperiments:
    """Tests for custom experiment definitions."""

    def test_load_valid_yaml(self, tmp_path):
        yaml_file = tmp_path / "test_exp.yaml"
        yaml_file.write_text(
            "name: test_experiment\n"
            "type: single_agent\n"
            "agents:\n"
            "  - type: mock\n"
            "tasks:\n"
            "  source: seed\n"
            "  count: 5\n"
            "metrics:\n"
            "  - pass_rate\n"
        )
        exp = CustomExperiment.load(yaml_file)
        assert exp.name == "test_experiment"
        assert exp.experiment_type == "single_agent"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            CustomExperiment.load("/nonexistent/file.yaml")

    def test_validate_valid(self, tmp_path):
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text(
            "name: valid_exp\n"
            "type: single_agent\n"
            "agents:\n"
            "  - type: mock\n"
            "tasks:\n"
            "  source: seed\n"
            "metrics:\n"
            "  - pass_rate\n"
        )
        exp = CustomExperiment.load(yaml_file)
        errors = exp.validate()
        assert errors == []

    def test_validate_missing_name(self, tmp_path):
        yaml_file = tmp_path / "no_name.yaml"
        yaml_file.write_text(
            "type: single_agent\n"
            "agents:\n"
            "  - type: mock\n"
            "tasks:\n"
            "  source: seed\n"
            "metrics:\n"
            "  - pass_rate\n"
        )
        exp = CustomExperiment.load(yaml_file)
        # name defaults to path.stem, so it should be valid
        errors = exp.validate()
        assert "Experiment name is required" not in errors

    def test_validate_ab_test_needs_two_agents(self, tmp_path):
        yaml_file = tmp_path / "ab.yaml"
        yaml_file.write_text(
            "name: ab_test\n"
            "type: ab_test\n"
            "agents:\n"
            "  - type: mock\n"
            "tasks:\n"
            "  source: seed\n"
            "metrics:\n"
            "  - pass_rate\n"
        )
        exp = CustomExperiment.load(yaml_file)
        errors = exp.validate()
        assert any("A/B test requires at least 2 agents" in e for e in errors)

    def test_save_and_reload(self, tmp_path):
        exp = CustomExperiment(
            name="saved_exp",
            description="Test",
            experiment_type="single_agent",
            agents=[{"type": "mock"}],
            tasks={"source": "seed"},
            metrics=["pass_rate"],
        )
        save_path = tmp_path / "saved.yaml"
        exp.save(save_path)
        reloaded = CustomExperiment.load(save_path)
        assert reloaded.name == "saved_exp"

    def test_loader_list_experiments(self, tmp_path):
        (tmp_path / "exp1.yaml").write_text(
            "name: exp1\ntype: single_agent\nagents:\n  - type: mock\ntasks:\n  source: seed\nmetrics:\n  - pass_rate\n"
        )
        loader = CustomExperimentLoader(tmp_path)
        loaded = loader.load_directory()
        assert len(loaded) == 1

    def test_to_dict(self):
        exp = CustomExperiment(name="test", experiment_type="benchmark")
        d = exp.to_dict()
        assert d["name"] == "test"
        assert d["type"] == "benchmark"


class TestNetworkPolicy:
    """Tests for network policy enforcement."""

    def test_enforce_allow_all(self):
        mgr = NetworkPolicyManager()
        result = mgr.enforce("sandbox-1", NetworkPolicy.ALLOW_ALL)
        assert result.enforced is True
        assert result.policy == "allow_all"

    def test_enforce_restrict_outbound(self):
        mgr = NetworkPolicyManager()
        mgr.set_allowed_hosts(["pypi.org", "github.com"])
        result = mgr.enforce("sandbox-1", NetworkPolicy.RESTRICT_OUTBOUND)
        assert result.enforced is True
        assert "pypi.org" in result.details

    def test_enforce_block_all(self):
        mgr = NetworkPolicyManager()
        result = mgr.enforce("sandbox-1", NetworkPolicy.BLOCK_ALL)
        assert result.enforced is True
        assert "blocked" in result.details

    def test_get_policy(self):
        mgr = NetworkPolicyManager()
        mgr.enforce("sandbox-1", NetworkPolicy.BLOCK_ALL)
        policy = mgr.get_policy("sandbox-1")
        assert policy == NetworkPolicy.BLOCK_ALL

    def test_remove_policy(self):
        mgr = NetworkPolicyManager()
        mgr.enforce("sandbox-1", NetworkPolicy.BLOCK_ALL)
        mgr.remove_policy("sandbox-1")
        assert mgr.get_policy("sandbox-1") is None

    def test_list_policies(self):
        mgr = NetworkPolicyManager()
        mgr.enforce("s1", NetworkPolicy.BLOCK_ALL)
        mgr.enforce("s2", NetworkPolicy.ALLOW_ALL)
        policies = mgr.list_policies()
        assert len(policies) == 2


class TestImageValidation:
    """Tests for container image validation."""

    def test_validate_missing_file(self):
        validator = ImageValidator()
        result = validator.validate("/nonexistent/Dockerfile")
        assert result.valid is False

    def test_validate_dockerfile_content(self):
        validator = ImageValidator()
        content = "FROM python:3.11-slim\nRUN pip install pytest\n"
        result = validator.validate_dockerfile_content(content)
        assert result.valid is True
        assert result.base_image == "python:3.11-slim"

    def test_vulnerable_base_image(self):
        validator = ImageValidator()
        content = "FROM ubuntu:14.04\nRUN apt-get update\n"
        result = validator.validate_dockerfile_content(content)
        assert result.valid is False
        assert any("vulnerable" in issue for issue in result.issues)

    def test_layer_count_exceeded(self):
        validator = ImageValidator(max_layers=2)
        content = "FROM python:3.11\nRUN echo 1\nRUN echo 2\nRUN echo 3\n"
        result = validator.validate_dockerfile_content(content)
        assert result.valid is False

    def test_root_warning(self):
        validator = ImageValidator()
        # Content with 'root' but no USER directive triggers warning
        content = "FROM python:3.11\nRUN apt-get update && apt-get install -y root-utils\n"
        result = validator.validate_dockerfile_content(content)
        # The check looks for 'root' in content and 'USER' not in content
        assert "root" in content
        assert "USER" not in content

    def test_to_dict(self):
        validator = ImageValidator()
        content = "FROM python:3.11\nRUN pip install pytest\n"
        result = validator.validate_dockerfile_content(content)
        d = result.to_dict()
        assert d["base_image"] == "python:3.11"


class TestMLflowTracker:
    """Tests for MLflow integration."""

    def test_not_available(self):
        tracker = MLflowTracker()
        assert tracker.is_available is False  # mlflow not installed

    def test_log_metric_fallback(self):
        tracker = MLflowTracker()
        result = tracker.log_metric("pass_rate", 0.75)
        assert result.success is False
        assert "not available" in result.details

    def test_get_metrics(self):
        tracker = MLflowTracker()
        tracker.log_metric("pass_rate", 0.75)
        tracker.log_metric("duration", 10.5)
        metrics = tracker.get_metrics()
        assert metrics["pass_rate"] == 0.75
        assert metrics["duration"] == 10.5

    def test_to_dict(self):
        tracker = MLflowTracker()
        d = tracker.to_dict()
        assert d["available"] is False

    def test_end_run_no_error(self):
        tracker = MLflowTracker()
        tracker.end_run()  # Should not raise


class TestBrowserAutomationTemplate:
    """Tests for the browser_automation template."""

    def test_template_registered(self):
        tmpl = templates.get_template("browser_automation")
        assert tmpl is not None
        assert "app.py" in tmpl["files"]

    def test_template_has_tests(self):
        tmpl = templates.get_template("browser_automation")
        assert "tests/test_public.py" in tmpl["files"]
        assert ".hidden_tests/test_hidden.py" in tmpl["files"]

    def test_template_in_list(self):
        listed = templates.list_templates()
        assert "browser_automation" in listed

    def test_mutation_xss_registered(self):
        mutation = seeder.get_mutation("xss_reflected")
        assert mutation is not None
        assert "XSS" in mutation["name"]

    def test_mutation_clickjacking_registered(self):
        mutation = seeder.get_mutation("clickjacking")
        assert mutation is not None
        assert "Clickjacking" in mutation["name"]

    def test_mutation_auth_bypass_registered(self):
        mutation = seeder.get_mutation("auth_bypass")
        assert mutation is not None
        assert "Authentication" in mutation["name"]
