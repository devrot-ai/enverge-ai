"""Tests for v0.4 features: multi-agent, parallel, local sandbox, variants,
curriculum persistence, and leaderboard."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from forge.core.schemas import (
    AgentConfig,
    CurriculumState,
    CurriculumStrategy,
    RunConfig,
    RunResult,
    RunStatus,
    TaskCategory,
    TaskSpec,
    WorldSpec,
)


# ---------------------------------------------------------------------------
# Multi-Agent Runner Tests
# ---------------------------------------------------------------------------


class TestMultiAgentRunner:
    """Test the MultiAgentRunner."""

    def test_import(self):
        """Should import MultiAgentRunner."""
        from forge.runner.multi_agent import MultiAgentRunner, MultiAgentReport, AgentComparison
        assert MultiAgentRunner is not None
        assert MultiAgentReport is not None
        assert AgentComparison is not None

    def test_agent_comparison_pass_rate(self):
        """Should calculate pass rate correctly."""
        from forge.runner.multi_agent import AgentComparison

        comp = AgentComparison(agent_type="mock", agent_id="test")
        comp.total_tasks = 10
        comp.passed = 7
        assert comp.pass_rate == 0.7

    def test_agent_comparison_zero_tasks(self):
        """Should return 0 pass rate for zero tasks."""
        from forge.runner.multi_agent import AgentComparison

        comp = AgentComparison(agent_type="mock", agent_id="test")
        assert comp.pass_rate == 0.0
        assert comp.avg_duration == 0.0

    def test_agent_comparison_to_dict(self):
        """Should serialize to dictionary."""
        from forge.runner.multi_agent import AgentComparison

        comp = AgentComparison(
            agent_type="mock",
            agent_id="test",
            total_tasks=5,
            passed=3,
            failed=2,
            total_duration=10.0,
        )
        d = comp.to_dict()
        assert d["agent_type"] == "mock"
        assert d["pass_rate"] == 0.6
        assert d["avg_duration"] == 2.0

    def test_multi_agent_report_summary(self):
        """Should generate summary."""
        from forge.runner.multi_agent import MultiAgentReport, AgentComparison

        report = MultiAgentReport(task_count=5)
        comp = AgentComparison(
            agent_type="mock",
            agent_id="test",
            total_tasks=5,
            passed=3,
        )
        report.add_comparison(comp)
        summary = report.generate_summary()
        assert summary["task_count"] == 5
        assert summary["agent_count"] == 1

    def test_multi_agent_report_markdown(self):
        """Should generate Markdown table."""
        from forge.runner.multi_agent import MultiAgentReport, AgentComparison

        report = MultiAgentReport(task_count=3)
        comp = AgentComparison(
            agent_type="mock",
            agent_id="test",
            total_tasks=3,
            passed=2,
            total_duration=6.0,
        )
        report.add_comparison(comp)
        md = report.to_markdown()
        assert "mock" in md
        assert "| Agent |" in md

    def test_multi_agent_runner_init(self):
        """Should initialize with default registry."""
        from forge.runner.multi_agent import MultiAgentRunner
        from forge.agents.registry import get_registry

        runner = MultiAgentRunner(registry=get_registry())
        assert runner.registry is not None

    def test_multi_agent_runner_with_registry(self):
        """Should use provided registry."""
        from forge.runner.multi_agent import MultiAgentRunner
        from forge.agents.registry import AgentRegistry

        registry = AgentRegistry()
        runner = MultiAgentRunner(registry=registry)
        assert runner.registry is registry


# ---------------------------------------------------------------------------
# Parallel Runner Tests
# ---------------------------------------------------------------------------


class TestParallelRunner:
    """Test the ParallelRunner."""

    def test_import(self):
        """Should import ParallelRunner."""
        from forge.runner.parallel import ParallelRunner, ParallelRunResult
        assert ParallelRunner is not None
        assert ParallelRunResult is not None

    def test_parallel_run_result_pass_rate(self):
        """Should calculate pass rate correctly."""
        from forge.runner.parallel import ParallelRunResult

        result = ParallelRunResult(agent_type="mock")
        result.completed = 10
        result.passed = 7
        assert result.pass_rate == 0.7

    def test_parallel_run_result_zero_completed(self):
        """Should return 0 pass rate for zero completed."""
        from forge.runner.parallel import ParallelRunResult

        result = ParallelRunResult(agent_type="mock")
        assert result.pass_rate == 0.0

    def test_parallel_run_result_to_dict(self):
        """Should serialize to dictionary."""
        from forge.runner.parallel import ParallelRunResult

        result = ParallelRunResult(
            agent_type="mock",
            total_tasks=5,
            completed=5,
            passed=3,
            failed=2,
            total_duration=10.0,
        )
        d = result.to_dict()
        assert d["agent_type"] == "mock"
        assert d["pass_rate"] == 0.6

    def test_parallel_runner_init(self):
        """Should initialize with default settings."""
        from forge.runner.parallel import ParallelRunner
        from forge.agents.registry import get_registry

        runner = ParallelRunner(registry=get_registry())
        assert runner.max_workers == 4

    def test_parallel_runner_custom_workers(self):
        """Should accept custom worker count."""
        from forge.runner.parallel import ParallelRunner
        from forge.agents.registry import get_registry

        runner = ParallelRunner(registry=get_registry(), max_workers=8)
        assert runner.max_workers == 8


# ---------------------------------------------------------------------------
# Local Sandbox Tests
# ---------------------------------------------------------------------------


class TestLocalSandbox:
    """Test the LocalSandbox."""

    def test_import(self):
        """Should import LocalSandbox."""
        from forge.sandbox.local import LocalSandbox, LocalSandboxResult
        assert LocalSandbox is not None
        assert LocalSandboxResult is not None

    def test_sandbox_init(self):
        """Should initialize with default timeout."""
        from forge.sandbox.local import LocalSandbox

        sandbox = LocalSandbox()
        assert sandbox.timeout == 60

    def test_sandbox_custom_timeout(self):
        """Should accept custom timeout."""
        from forge.sandbox.local import LocalSandbox

        sandbox = LocalSandbox(timeout=30)
        assert sandbox.timeout == 30

    def test_sandbox_no_tests_dir(self, tmp_path):
        """Should return error when no tests directory."""
        from forge.sandbox.local import LocalSandbox

        sandbox = LocalSandbox()
        result = sandbox.run_tests(str(tmp_path))
        assert result.passed is False
        assert "No tests directory" in result.stderr

    def test_sandbox_hidden_no_dir(self, tmp_path):
        """Should pass when no hidden tests directory."""
        from forge.sandbox.local import LocalSandbox

        sandbox = LocalSandbox()
        result = sandbox.run_hidden_tests(str(tmp_path))
        assert result.passed is True

    def test_sandbox_parse_output_passed(self):
        """Should parse pytest passed output."""
        from forge.sandbox.local import LocalSandbox

        sandbox = LocalSandbox()
        run, passed, failed, errors = sandbox._parse_output("5 passed in 1.23s")
        assert passed == 5
        assert run == 5

    def test_sandbox_parse_output_mixed(self):
        """Should parse mixed pytest output."""
        from forge.sandbox.local import LocalSandbox

        sandbox = LocalSandbox()
        run, passed, failed, errors = sandbox._parse_output("3 passed, 2 failed in 1.23s")
        assert passed == 3
        assert failed == 2
        assert run == 5


# ---------------------------------------------------------------------------
# Variant Generator Tests
# ---------------------------------------------------------------------------


class TestVariantGenerator:
    """Test the VariantGenerator."""

    def test_import(self):
        """Should import VariantGenerator."""
        from forge.task_factory.variants import VariantGenerator, TaskVariant
        assert VariantGenerator is not None
        assert TaskVariant is not None

    def test_task_variant_to_dict(self):
        """Should serialize variant to dictionary."""
        from forge.task_factory.variants import TaskVariant

        variant = TaskVariant(
            task_id="VARIANT-001",
            template="task_manager_api",
            mutation="pagination_boundary",
            category="bug_repair",
            description="Test variant",
            difficulty=3,
            constraints=["Must not modify API"],
            verification={"method": "test_execution"},
            capabilities=["pagination"],
        )
        d = variant.to_dict()
        assert d["task_id"] == "VARIANT-001"
        assert d["template"] == "task_manager_api"

    def test_task_variant_to_task_spec(self):
        """Should convert to TaskSpec."""
        from forge.task_factory.variants import TaskVariant

        variant = TaskVariant(
            task_id="VARIANT-001",
            template="task_manager_api",
            mutation="pagination_boundary",
            category="bug_repair",
            description="Test variant",
            difficulty=3,
            constraints=["Must not modify API"],
            verification={"method": "test_execution"},
            capabilities=["pagination"],
        )
        spec = variant.to_task_spec()
        assert spec.task_id == "VARIANT-001"
        assert spec.difficulty_level == 3

    def test_variant_generator_init(self, tmp_path):
        """Should initialize with custom variants dir."""
        from forge.task_factory.variants import VariantGenerator

        gen = VariantGenerator(variants_dir=str(tmp_path))
        assert gen.variants_dir == tmp_path

    def test_load_variants_empty(self, tmp_path):
        """Should return empty list for non-existent variants."""
        from forge.task_factory.variants import VariantGenerator

        gen = VariantGenerator(variants_dir=str(tmp_path))
        variants = gen.load_variants("nonexistent")
        assert variants == []

    def test_generate_variants_unknown_template(self, tmp_path):
        """Should return empty list for unknown template."""
        from forge.task_factory.variants import VariantGenerator

        gen = VariantGenerator(variants_dir=str(tmp_path))
        # Unknown template has no mutations, so returns empty
        variants = gen.generate_variants("unknown_template_xyz", count=3)
        assert variants == []

    def test_capabilities_map(self):
        """Should have capabilities for all templates."""
        from forge.task_factory.variants import VariantGenerator

        gen = VariantGenerator()
        caps = gen._get_capabilities_for_template("task_manager_api")
        assert "pagination" in caps
        unknown = gen._get_capabilities_for_template("unknown")
        assert unknown == ["bug_repair"]


# ---------------------------------------------------------------------------
# Curriculum Persistence Tests
# ---------------------------------------------------------------------------


class TestCurriculumPersistence:
    """Test the CurriculumPersistence."""

    def test_import(self):
        """Should import CurriculumPersistence."""
        from forge.curriculum.persistence import CurriculumPersistence, CurriculumSnapshot
        assert CurriculumPersistence is not None
        assert CurriculumSnapshot is not None

    def test_save_and_load(self, tmp_path):
        """Should save and load curriculum state."""
        from forge.curriculum.persistence import CurriculumPersistence

        curriculum = CurriculumState(
            curriculum_id="test-curriculum",
            strategy=CurriculumStrategy.ADAPTIVE,
            capability_scores={"pagination": 0.8},
            selected_tasks=["task-001", "task-002"],
        )

        persist = CurriculumPersistence(persist_dir=str(tmp_path))
        path = persist.save(curriculum, "test_snapshot")
        assert path.exists()

        snapshot = persist.load("test_snapshot")
        assert snapshot.curriculum_id == "test-curriculum"
        assert snapshot.strategy == "adaptive"

    def test_list_snapshots(self, tmp_path):
        """Should list saved snapshots."""
        from forge.curriculum.persistence import CurriculumPersistence

        curriculum = CurriculumState(
            curriculum_id="test-1",
            strategy=CurriculumStrategy.STATIC,
            capability_scores={},
            selected_tasks=["task-001"],
        )

        persist = CurriculumPersistence(persist_dir=str(tmp_path))
        persist.save(curriculum, "snap1")
        persist.save(curriculum, "snap2")

        snapshots = persist.list_snapshots()
        assert len(snapshots) == 2

    def test_list_snapshots_empty(self, tmp_path):
        """Should return empty list when no snapshots."""
        from forge.curriculum.persistence import CurriculumPersistence

        persist = CurriculumPersistence(persist_dir=str(tmp_path / "empty"))
        snapshots = persist.list_snapshots()
        assert snapshots == []

    def test_load_missing_snapshot(self, tmp_path):
        """Should raise FileNotFoundError for missing snapshot."""
        from forge.curriculum.persistence import CurriculumPersistence

        persist = CurriculumPersistence(persist_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            persist.load("nonexistent")

    def test_export_and_import(self, tmp_path):
        """Should export to and import from specific file."""
        from forge.curriculum.persistence import CurriculumPersistence

        curriculum = CurriculumState(
            curriculum_id="export-test",
            strategy=CurriculumStrategy.RANDOM,
            capability_scores={"search": 0.5},
            selected_tasks=["task-001"],
        )

        persist = CurriculumPersistence(persist_dir=str(tmp_path))
        output = tmp_path / "exported.json"
        persist.export(curriculum, output)
        assert output.exists()

        imported = persist.import_(output)
        assert imported.curriculum_id == "export-test"

    def test_snapshot_to_dict(self):
        """Should serialize snapshot to dictionary."""
        from forge.curriculum.persistence import CurriculumSnapshot

        snapshot = CurriculumSnapshot(
            curriculum_id="test",
            strategy="adaptive",
            capability_scores={"x": 0.9},
            selected_tasks=["t1"],
            history=[],
            saved_at="2024-01-01T00:00:00",
        )
        d = snapshot.to_dict()
        assert d["curriculum_id"] == "test"
        assert d["capability_scores"]["x"] == 0.9

    def test_snapshot_from_dict(self):
        """Should deserialize snapshot from dictionary."""
        from forge.curriculum.persistence import CurriculumSnapshot

        data = {
            "curriculum_id": "test",
            "strategy": "static",
            "capability_scores": {},
            "selected_tasks": [],
            "history": [],
            "saved_at": "2024-01-01T00:00:00",
        }
        snapshot = CurriculumSnapshot.from_dict(data)
        assert snapshot.curriculum_id == "test"


# ---------------------------------------------------------------------------
# Leaderboard Tests
# ---------------------------------------------------------------------------


class TestLeaderboard:
    """Test the Leaderboard."""

    def test_import(self):
        """Should import Leaderboard."""
        from forge.evaluation.leaderboard import Leaderboard, LeaderboardEntry, AgentRanking
        assert Leaderboard is not None
        assert LeaderboardEntry is not None
        assert AgentRanking is not None

    def test_add_result(self, tmp_path):
        """Should add a result to the leaderboard."""
        from forge.evaluation.leaderboard import Leaderboard, LeaderboardEntry

        entry = LeaderboardEntry(
            run_id="run-001",
            agent_type="mock",
            task_id="task-001",
            template="task_manager_api",
            difficulty=3,
            passed=True,
            duration_seconds=5.0,
            failure_category=None,
            timestamp="2024-01-01T00:00:00",
        )

        lb = Leaderboard(data_file=str(tmp_path / "lb.json"))
        lb.add_result(entry)
        assert len(lb._entries) == 1

    def test_get_rankings(self, tmp_path):
        """Should return rankings sorted by pass rate."""
        from forge.evaluation.leaderboard import Leaderboard, LeaderboardEntry

        lb = Leaderboard(data_file=str(tmp_path / "lb.json"))

        # Add entries for two agents
        lb.add_result(LeaderboardEntry(
            run_id="run-001", agent_type="mock", task_id="t1",
            template="t1", difficulty=1, passed=True, duration_seconds=1.0,
            failure_category=None, timestamp="2024-01-01",
        ))
        lb.add_result(LeaderboardEntry(
            run_id="run-002", agent_type="mock", task_id="t2",
            template="t1", difficulty=1, passed=False, duration_seconds=2.0,
            failure_category="agent_failure", timestamp="2024-01-01",
        ))
        lb.add_result(LeaderboardEntry(
            run_id="run-003", agent_type="rule_based", task_id="t1",
            template="t1", difficulty=1, passed=True, duration_seconds=3.0,
            failure_category=None, timestamp="2024-01-01",
        ))

        rankings = lb.get_rankings()
        assert len(rankings) == 2
        # rule_based has 100% pass rate, should be first
        assert rankings[0].agent_type == "rule_based"
        assert rankings[0].pass_rate == 1.0

    def test_compare_agents(self, tmp_path):
        """Should compare multiple agents."""
        from forge.evaluation.leaderboard import Leaderboard, LeaderboardEntry

        lb = Leaderboard(data_file=str(tmp_path / "lb.json"))
        lb.add_result(LeaderboardEntry(
            run_id="run-001", agent_type="mock", task_id="t1",
            template="t1", difficulty=1, passed=True, duration_seconds=1.0,
            failure_category=None, timestamp="2024-01-01",
        ))

        comparison = lb.compare_agents(["mock"])
        assert comparison["agent_count"] == 1
        assert comparison["rankings"][0]["agent_type"] == "mock"

    def test_get_entries_filter(self, tmp_path):
        """Should filter entries by criteria."""
        from forge.evaluation.leaderboard import Leaderboard, LeaderboardEntry

        lb = Leaderboard(data_file=str(tmp_path / "lb.json"))
        lb.add_result(LeaderboardEntry(
            run_id="run-001", agent_type="mock", task_id="t1",
            template="t1", difficulty=1, passed=True, duration_seconds=1.0,
            failure_category=None, timestamp="2024-01-01",
        ))
        lb.add_result(LeaderboardEntry(
            run_id="run-002", agent_type="mock", task_id="t2",
            template="t1", difficulty=1, passed=False, duration_seconds=2.0,
            failure_category="agent_failure", timestamp="2024-01-01",
        ))

        passed_only = lb.get_entries(passed=True)
        assert len(passed_only) == 1
        assert passed_only[0].passed is True

    def test_export(self, tmp_path):
        """Should export leaderboard as JSON."""
        from forge.evaluation.leaderboard import Leaderboard, LeaderboardEntry

        lb = Leaderboard(data_file=str(tmp_path / "lb.json"))
        lb.add_result(LeaderboardEntry(
            run_id="run-001", agent_type="mock", task_id="t1",
            template="t1", difficulty=1, passed=True, duration_seconds=1.0,
            failure_category=None, timestamp="2024-01-01",
        ))

        output = tmp_path / "export.json"
        json_str = lb.export(output)
        assert output.exists()
        data = json.loads(json_str)
        assert data["entry_count"] == 1

    def test_to_markdown(self, tmp_path):
        """Should generate Markdown leaderboard."""
        from forge.evaluation.leaderboard import Leaderboard, LeaderboardEntry

        lb = Leaderboard(data_file=str(tmp_path / "lb.json"))
        lb.add_result(LeaderboardEntry(
            run_id="run-001", agent_type="mock", task_id="t1",
            template="t1", difficulty=1, passed=True, duration_seconds=1.0,
            failure_category=None, timestamp="2024-01-01",
        ))

        md = lb.to_markdown()
        assert "# Benchmark Leaderboard" in md
        assert "mock" in md

    def test_leaderboard_entry_serialization(self):
        """Should serialize and deserialize entry."""
        from forge.evaluation.leaderboard import LeaderboardEntry

        entry = LeaderboardEntry(
            run_id="run-001",
            agent_type="mock",
            task_id="task-001",
            template="task_manager_api",
            difficulty=3,
            passed=True,
            duration_seconds=5.5,
            failure_category=None,
            timestamp="2024-01-01T00:00:00",
        )
        d = entry.to_dict()
        restored = LeaderboardEntry.from_dict(d)
        assert restored.run_id == "run-001"
        assert restored.agent_type == "mock"
        assert restored.passed is True

    def test_agent_ranking_pass_rate(self):
        """Should calculate pass rate correctly."""
        from forge.evaluation.leaderboard import AgentRanking

        ranking = AgentRanking(
            agent_type="mock",
            total_runs=10,
            passed=7,
            failed=3,
        )
        assert ranking.pass_rate == 0.7

    def test_agent_ranking_zero_runs(self):
        """Should return 0 pass rate for zero runs."""
        from forge.evaluation.leaderboard import AgentRanking

        ranking = AgentRanking(agent_type="mock")
        assert ranking.pass_rate == 0.0

    def test_add_results_batch(self, tmp_path):
        """Should add multiple results at once."""
        from forge.evaluation.leaderboard import Leaderboard, LeaderboardEntry

        lb = Leaderboard(data_file=str(tmp_path / "lb.json"))
        entries = [
            LeaderboardEntry(
                run_id=f"run-{i}", agent_type="mock", task_id=f"t{i}",
                template="t1", difficulty=1, passed=True, duration_seconds=1.0,
                failure_category=None, timestamp="2024-01-01",
            )
            for i in range(5)
        ]
        lb.add_results(entries)
        assert len(lb._entries) == 5
