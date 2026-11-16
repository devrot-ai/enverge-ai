"""Tests for v0.6 features: error injection, adversarial agent, composite mutations,
cross-template analysis, evaluation reports, and config_manager template."""

import os
import tempfile
from pathlib import Path

import pytest

# Error Injection
from forge.evaluation.error_injection import ErrorInjector, ErrorInjectionResult

# Adversarial Agent
from forge.agents.adversarial import AdversarialAgent, AdversarialResult
from forge.agents.mock_agent import MockAgent

# Composite Mutations
from forge.world_factory.composite import CompositeManager, CompositeMutation

# Cross-Template Analysis
from forge.world_factory.cross_template import (
    CrossTemplateAnalyzer,
    CrossTemplateResult,
)

# Evaluation Report
from forge.evaluation.report import EvaluationReport, EvaluationStats

# Core schemas
from forge.core.schemas import (
    RunResult,
    RunStatus,
    TaskSpec,
    TaskCategory,
    VerificationResult,
    WorldSpec,
)

# Seeder
from forge.world_factory import seeder
from forge.world_factory.seeder import MutationPattern

# Templates
from forge.world_factory import templates


class TestErrorInjector:
    """Tests for error injection module."""

    def test_inject_import_error(self, tmp_path):
        """Import error should be injectable."""
        # Create a Python file
        (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
        injector = ErrorInjector()
        result = injector.inject(str(tmp_path), "import_error")
        assert result.injected is True
        content = (tmp_path / "app.py").read_text()
        assert "import" in content

    def test_inject_type_error(self, tmp_path):
        """Type error should be injectable."""
        (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
        injector = ErrorInjector()
        result = injector.inject(str(tmp_path), "type_error")
        assert result.injected is True

    def test_inject_attribute_error(self, tmp_path):
        """Attribute error should be injectable."""
        (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
        injector = ErrorInjector()
        result = injector.inject(str(tmp_path), "attribute_error")
        assert result.injected is True

    def test_inject_runtime_error(self, tmp_path):
        """Runtime error should be injectable."""
        (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
        injector = ErrorInjector()
        result = injector.inject(str(tmp_path), "runtime_error")
        assert result.injected is True

    def test_inject_syntax_error(self, tmp_path):
        """Syntax error should be injectable."""
        (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
        injector = ErrorInjector()
        result = injector.inject(str(tmp_path), "syntax_error")
        assert result.injected is True

    def test_unknown_error_type(self, tmp_path):
        """Unknown error type should not inject."""
        (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
        injector = ErrorInjector()
        result = injector.inject(str(tmp_path), "unknown_error")
        assert result.injected is False

    def test_no_python_files(self, tmp_path):
        """Empty workspace should not inject."""
        injector = ErrorInjector()
        result = injector.inject(str(tmp_path), "import_error")
        assert result.injected is False

    def test_inject_multiple(self, tmp_path):
        """Multiple errors should be injectable."""
        (tmp_path / "app.py").write_text("def hello():\n    return 'world'\n")
        injector = ErrorInjector()
        results = injector.inject_multiple(str(tmp_path), count=3)
        assert len(results) == 3

    def test_result_serialization(self):
        """ErrorInjectionResult should serialize."""
        result = ErrorInjectionResult(
            error_type="import_error",
            injected=True,
            details="Test injection",
        )
        d = result.to_dict()
        assert d["error_type"] == "import_error"
        assert d["injected"] is True


class TestAdversarialAgent:
    """Tests for adversarial agent wrapper."""

    def _make_mock_agent(self):
        from forge.core.schemas import AgentConfig
        cfg = AgentConfig(
            agent_id="mock-test",
            agent_type="mock",
            metadata={"scenario": "success"},
        )
        return MockAgent(config=cfg)

    def test_agent_type(self):
        """Agent type should include wrapped agent."""
        base = self._make_mock_agent()
        adv = AdversarialAgent(base, error_rate=0.1)
        assert "adversarial" in adv.agent_type

    def test_initialization(self):
        """Adversarial agent should initialize correctly."""
        base = self._make_mock_agent()
        adv = AdversarialAgent(base, error_rate=0.5, seed=42)
        assert adv.error_rate == 0.5
        assert len(adv.error_injections) == 0

    def test_custom_error_types(self):
        """Custom error types should be accepted."""
        base = self._make_mock_agent()
        adv = AdversarialAgent(
            base,
            error_rate=0.1,
            error_types=["import_error", "type_error"],
        )
        assert adv.error_types == ["import_error", "type_error"]

    def test_robustness_calculation(self):
        """Robustness score should be calculated."""
        base = self._make_mock_agent()
        adv = AdversarialAgent(base, error_rate=0.1)
        score = adv._calculate_robustness()
        assert score["robustness_score"] == 1.0  # no errors yet

    def test_adversarial_result_serialization(self):
        """AdversarialResult should serialize."""
        run = RunResult(
            run_id="test-1",
            task_id="t1",
            agent_id="mock",
            status=RunStatus.COMPLETED,
        )
        adv_result = AdversarialResult(
            base_result=run,
            robustness_score=0.8,
            errors_handled=4,
            errors_total=5,
        )
        d = adv_result.to_dict()
        assert d["robustness_score"] == 0.8
        assert d["errors_handled"] == 4


class TestCompositeManager:
    """Tests for composite mutations."""

    def test_create_composite(self):
        """Composite should be created from mutation names."""
        mgr = CompositeManager()
        composite = mgr.create("task_manager_api", ["pagination_boundary", "empty_search"])
        assert composite.template_name == "task_manager_api"
        assert len(composite.mutation_names) == 2

    def test_composite_serialization(self):
        """CompositeMutation should serialize."""
        composite = CompositeMutation(
            template_name="test",
            mutation_names=["m1", "m2"],
        )
        d = composite.to_dict()
        assert d["template_name"] == "test"
        assert d["is_composite"] is True

    def test_conflict_detection(self):
        """Conflicts should be detected for overlapping patterns."""
        mgr = CompositeManager()
        # Same mutation twice should conflict
        overlap = mgr._patterns_overlap(r"def hello", r"def hello")
        assert overlap is True

    def test_no_conflict(self):
        """Different patterns should not conflict."""
        mgr = CompositeManager()
        overlap = mgr._patterns_overlap(r"def hello", r"return world")
        assert overlap is False

    def test_apply_composite(self):
        """Composite should apply all mutations."""
        mgr = CompositeManager()
        content = "def hello():\n    return 'world'\n"
        composite = CompositeMutation(
            template_name="test",
            mutation_names=["m1"],
        )
        # Without actual mutations, content won't change
        result = mgr.apply_composite(content, composite)
        # Returns None if no change
        assert result is None

    def test_create_task_spec(self):
        """Task spec should be created for composite."""
        mgr = CompositeManager()
        world = WorldSpec(
            world_type="code_repair",
            template_name="test",
        )
        world.world_id = "w1"
        composite = CompositeMutation(
            template_name="test",
            mutation_names=["m1", "m2"],
        )
        task = mgr.create_task_spec(world, composite, "t1")
        assert task.task_id == "t1"
        assert task.metadata["is_composite"] is True
        assert task.metadata["mutation_count"] == 2

    def test_compatible_mutations_empty(self):
        """Compatible mutations should return empty for single mutation."""
        mgr = CompositeManager()
        result = mgr.get_compatible_mutations("test", {})
        assert result == []


class TestCrossTemplateAnalyzer:
    """Tests for cross-template analysis."""

    def test_analyze_mutations(self):
        """Mutations should be analyzed across templates."""
        analyzer = CrossTemplateAnalyzer()
        all_mutations = seeder._mutations
        # Convert to MutationPattern objects
        mutation_lists: dict[str, list[MutationPattern]] = {}
        for mid, mdata in all_mutations.items():
            mp = MutationPattern(
                name=mdata["id"],
                search_pattern=mdata["search_pattern"],
                replace_with=mdata["replace_with"],
                reference_fix=mdata.get("reference_fix", ""),
                capabilities=mdata.get("capabilities", []),
                difficulty=mdata.get("difficulty", 1),
                description=mdata.get("description", ""),
            )
            # Group by template (use mutation id prefix)
            template = "test"
            if template not in mutation_lists:
                mutation_lists[template] = []
            mutation_lists[template].append(mp)

        results = analyzer.analyze_mutations(mutation_lists)
        assert len(results) > 0

    def test_capability_coverage(self):
        """Capability coverage should be computed."""
        analyzer = CrossTemplateAnalyzer()
        coverage = analyzer.get_capability_coverage({})
        assert coverage == {}

    def test_template_coverage(self):
        """Template coverage should be computed."""
        analyzer = CrossTemplateAnalyzer()
        coverage = analyzer.get_template_coverage({})
        assert coverage == {}

    def test_generate_report(self):
        """Report should be generated."""
        analyzer = CrossTemplateAnalyzer()
        report = analyzer.generate_report({})
        assert "# Cross-Template Mutation Analysis" in report

    def test_to_dict(self):
        """Analysis should serialize to dict."""
        analyzer = CrossTemplateAnalyzer()
        d = analyzer.to_dict({})
        assert "cross_template_mutations" in d
        assert "capability_coverage" in d


class TestEvaluationReport:
    """Tests for evaluation report generator."""

    def _make_run(self, passed, agent_id="mock", duration=1.0):
        status = RunStatus.COMPLETED if passed else RunStatus.FAILED
        run = RunResult(
            run_id=f"run-{passed}",
            task_id="t1",
            agent_id=agent_id,
            status=status,
        )
        run.passed = passed
        run.verification = VerificationResult(
            run_id=f"run-{passed}",
            passed=passed,
        )
        return run

    def _make_task(self, template="test", difficulty=1):
        return TaskSpec(
            task_id="t1",
            world_id="w1",
            description="Test",
            category=TaskCategory.BUG_REPAIR,
            difficulty_level=difficulty,
            metadata={"template_name": template},
        )

    def test_empty_results(self):
        """Empty results should produce zero stats."""
        report = EvaluationReport()
        stats = report.generate([], [])
        assert stats.total_runs == 0
        assert stats.pass_rate == 0.0

    def test_all_passed(self):
        """All passed should give 100% rate."""
        report = EvaluationReport()
        runs = [self._make_run(True) for _ in range(5)]
        tasks = [self._make_task() for _ in range(5)]
        stats = report.generate(runs, tasks)
        assert stats.pass_rate == 1.0
        assert stats.passed == 5

    def test_all_failed(self):
        """All failed should give 0% rate."""
        report = EvaluationReport()
        runs = [self._make_run(False) for _ in range(5)]
        tasks = [self._make_task() for _ in range(5)]
        stats = report.generate(runs, tasks)
        assert stats.pass_rate == 0.0
        assert stats.failed == 5

    def test_mixed_results(self):
        """Mixed results should compute correct rate."""
        report = EvaluationReport()
        runs = [self._make_run(True), self._make_run(False), self._make_run(True)]
        tasks = [self._make_task() for _ in range(3)]
        stats = report.generate(runs, tasks)
        assert stats.pass_rate == pytest.approx(2 / 3, abs=0.01)

    def test_template_breakdown(self):
        """Template pass rates should be computed."""
        report = EvaluationReport()
        runs = [
            self._make_run(True),
            self._make_run(False),
        ]
        tasks = [
            self._make_task(template="t1"),
            self._make_task(template="t1"),
        ]
        stats = report.generate(runs, tasks)
        assert "t1" in stats.template_pass_rates

    def test_agent_breakdown(self):
        """Agent pass rates should be computed."""
        report = EvaluationReport()
        runs = [
            self._make_run(True, agent_id="agent1"),
            self._make_run(False, agent_id="agent2"),
        ]
        tasks = [self._make_task() for _ in range(2)]
        stats = report.generate(runs, tasks)
        assert stats.agent_pass_rates["agent1"] == 1.0
        assert stats.agent_pass_rates["agent2"] == 0.0

    def test_markdown_report(self):
        """Markdown report should be generated."""
        report = EvaluationReport()
        stats = EvaluationStats(total_runs=10, passed=7, failed=3, pass_rate=0.7)
        md = report.generate_markdown(stats)
        assert "# Evaluation Report" in md
        assert "Total Runs" in md

    def test_json_report(self):
        """JSON report should be generated."""
        report = EvaluationReport()
        stats = EvaluationStats(total_runs=10, passed=7, failed=3, pass_rate=0.7)
        j = report.generate_json(stats)
        assert "stats" in j
        assert "recommendations" in j

    def test_stats_serialization(self):
        """EvaluationStats should serialize."""
        stats = EvaluationStats(
            total_runs=10,
            passed=7,
            failed=3,
            pass_rate=0.7,
        )
        d = stats.to_dict()
        assert d["total_runs"] == 10
        assert d["pass_rate"] == 0.7


class TestConfigManagerTemplate:
    """Tests for config_manager template."""

    def test_template_registered(self):
        """config_manager should be registered."""
        tmpl = templates.get_template("config_manager")
        assert tmpl is not None

    def test_template_has_files(self):
        """Template should have all required files."""
        tmpl = templates.get_template("config_manager")
        assert "app.py" in tmpl["files"]
        assert "tests/test_public.py" in tmpl["files"]
        assert ".hidden_tests/test_hidden.py" in tmpl["files"]

    def test_mutations_registered(self):
        """config_manager mutations should be registered."""
        assert seeder.get_mutation("env_override") is not None
        assert seeder.get_mutation("secret_exposure") is not None
        assert seeder.get_mutation("merge_conflict") is not None

    def test_world_generation(self, tmp_path):
        """World should be generated for config_manager."""
        from forge.world_factory.generator import WorldGenerator

        gen = WorldGenerator()
        world = gen.generate(
            template_name="config_manager",
            mutation_id="merge_conflict",
            seed=42,
        )
        assert world is not None
