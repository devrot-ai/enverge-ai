"""Tests for the new ForgeLab modules.

Covers: agents/tools, agents/registry, agents/config, runner/trajectory,
runner/lifecycle, evaluation/metrics, evaluation/scoring, evaluation/reports,
diagnosis/rules, diagnosis/triage, diagnosis/report, curriculum/capability_tracker,
curriculum/difficulty, curriculum/updater, curriculum/history, experiments/config,
experiments/comparison, experiments/artifacts, sandbox/executor, sandbox/reset,
sandbox/policies, task_factory/mutations, task_factory/difficulty,
task_factory/selection, training/adapter.
"""

import os
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Agents: Tools
# ---------------------------------------------------------------------------


class TestToolPathValidation:
    def test_validate_path_allows_valid_path(self, tmp_path):
        from forge.agents.tools import validate_path

        (tmp_path / "subdir").mkdir()
        result = validate_path(tmp_path, "subdir/file.py")
        assert result == tmp_path / "subdir" / "file.py"

    def test_validate_path_blocks_traversal(self, tmp_path):
        from forge.agents.tools import validate_path

        with pytest.raises(ValueError, match="Path traversal"):
            validate_path(tmp_path, "../secret.py")

    def test_validate_path_blocks_absolute_escape(self, tmp_path):
        from forge.agents.tools import validate_path

        with pytest.raises(ValueError, match="Path traversal"):
            validate_path(tmp_path, "/etc/passwd")

    def test_validate_path_empty_raises(self, tmp_path):
        from forge.agents.tools import validate_path

        with pytest.raises(ValueError, match="Empty path"):
            validate_path(tmp_path, "")


class TestToolExecutor:
    def test_list_files(self, tmp_path):
        from forge.agents.tools import ToolExecutor

        (tmp_path / "file1.py").write_text("print('hi')")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.py").write_text("print('world')")
        executor = ToolExecutor(tmp_path)
        result = executor.list_files({"path": "", "recursive": False})
        assert "file1.py" in result

    def test_read_file(self, tmp_path):
        from forge.agents.tools import ToolExecutor

        (tmp_path / "test.py").write_text("x = 42")
        executor = ToolExecutor(tmp_path)
        result = executor.read_file({"path": "test.py"})
        assert "x = 42" in result

    def test_write_file(self, tmp_path):
        from forge.agents.tools import ToolExecutor

        executor = ToolExecutor(tmp_path)
        result = executor.write_file({"path": "new.py", "content": "y = 10"})
        assert "Successfully wrote" in result
        assert (tmp_path / "new.py").read_text() == "y = 10"

    def test_search_code(self, tmp_path):
        from forge.agents.tools import ToolExecutor

        (tmp_path / "app.py").write_text("def hello():\n    return 'world'")
        executor = ToolExecutor(tmp_path)
        result = executor.search_code({"pattern": "hello", "path": "", "file_type": "*.py"})
        assert "hello" in result


class TestToolValidation:
    def test_validate_tool_args_valid(self):
        from forge.agents.tools import validate_tool_args

        args = validate_tool_args("read_file", {"path": "test.py"})
        assert args["path"] == "test.py"

    def test_validate_tool_args_missing_required(self):
        from forge.agents.tools import validate_tool_args

        with pytest.raises(ValueError, match="Missing required"):
            validate_tool_args("read_file", {})

    def test_validate_tool_args_unknown_tool(self):
        from forge.agents.tools import validate_tool_args

        with pytest.raises(ValueError, match="Unknown tool"):
            validate_tool_args("nonexistent", {})


# ---------------------------------------------------------------------------
# Agents: Registry
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    def test_register_and_create(self):
        from forge.agents.mock_agent import MockAgent
        from forge.agents.registry import AgentRegistry
        from forge.core.schemas import AgentConfig

        registry = AgentRegistry()
        registry.register("mock", lambda cfg: MockAgent(cfg, scenario="success"), MockAgent)
        config = AgentConfig(agent_type="mock")
        agent = registry.create(config)
        assert isinstance(agent, MockAgent)

    def test_list_types(self):
        from forge.agents.mock_agent import MockAgent
        from forge.agents.registry import AgentRegistry

        registry = AgentRegistry()
        registry.register("mock", lambda cfg: MockAgent(cfg, scenario="success"))
        registry.register("test", lambda cfg: MockAgent(cfg, scenario="failure"))
        types = registry.list_types()
        assert "mock" in types
        assert "test" in types

    def test_create_unknown_type(self):
        from forge.agents.registry import AgentRegistry
        from forge.core.schemas import AgentConfig

        registry = AgentRegistry()
        config = AgentConfig(agent_type="unknown")
        with pytest.raises(ValueError, match="Unknown agent type"):
            registry.create(config)


# ---------------------------------------------------------------------------
# Agents: Config
# ---------------------------------------------------------------------------


class TestAgentConfig:
    def test_create_mock_config(self):
        from forge.agents.config import create_mock_config

        config = create_mock_config("success")
        assert config.agent_type == "mock"
        assert config.metadata["scenario"] == "success"

    def test_load_from_env(self):
        from forge.agents.config import load_agent_config_from_env

        with patch.dict(os.environ, {"FORGELAB_MODEL": "gpt-4", "FORGELAB_MAX_STEPS": "100"}):
            config = load_agent_config_from_env()
            assert config.model == "gpt-4"
            assert config.max_steps == 100


# ---------------------------------------------------------------------------
# Runner: Trajectory
# ---------------------------------------------------------------------------


class TestTrajectoryIO:
    def test_save_and_load_trajectory(self, tmp_path):
        from forge.core.schemas import Trajectory, TrajectoryStep
        from forge.runner.trajectory import load_trajectory, save_trajectory

        traj = Trajectory(
            trajectory_id="traj-1",
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
        )
        traj.add_step(
            TrajectoryStep(
                step_index=0,
                observation="Start",
                action="read_file",
                tool_name="read_file",
                tool_arguments={"path": "app.py"},
                tool_result="def hello(): pass",
            )
        )

        filepath = save_trajectory(traj, tmp_path)
        loaded = load_trajectory(filepath)
        assert loaded.run_id == "run-1"
        assert len(loaded.steps) == 1

    def test_export_trajectory_summary(self):
        from forge.core.schemas import Trajectory, TrajectoryStep
        from forge.runner.trajectory import export_trajectory_summary

        traj = Trajectory(
            trajectory_id="traj-1",
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
        )
        traj.add_step(
            TrajectoryStep(
                step_index=0,
                observation="Start",
                action="read_file",
                tool_name="read_file",
            )
        )
        summary = export_trajectory_summary(traj)
        assert summary["total_steps"] == 1
        assert summary["tool_calls"]["read_file"] == 1


# ---------------------------------------------------------------------------
# Runner: Lifecycle
# ---------------------------------------------------------------------------


class TestRunLifecycle:
    def test_lifecycle_transitions(self):
        from forge.core.schemas import RunConfig
        from forge.runner.lifecycle import RunLifecycle, RunState

        config = RunConfig(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            timeout_seconds=300,
        )
        lifecycle = RunLifecycle(config)
        assert lifecycle.state == RunState.CREATED

        lifecycle.start()
        lifecycle.mark_agent_running()
        assert lifecycle.state == RunState.AGENT_RUNNING

        lifecycle.mark_complete()
        assert lifecycle.is_terminal()

    def test_lifecycle_timeout(self):
        import time

        from forge.core.schemas import RunConfig
        from forge.runner.lifecycle import RunLifecycle

        config = RunConfig(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            timeout_seconds=0,
        )
        lifecycle = RunLifecycle(config)
        lifecycle.start()
        time.sleep(0.1)  # Let time pass so timeout triggers
        assert lifecycle.check_timeout() is True


# ---------------------------------------------------------------------------
# Evaluation: Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_compute_success_rate(self):
        from forge.core.schemas import RunResult, RunStatus
        from forge.evaluation.metrics import compute_success_rate

        r1 = RunResult(run_id="r1", task_id="t1", agent_id="a1", status=RunStatus.COMPLETED)
        r1.passed = True
        r2 = RunResult(run_id="r2", task_id="t1", agent_id="a1", status=RunStatus.COMPLETED)
        r2.passed = False
        results = [r1, r2]
        rate = compute_success_rate(results)
        assert 0.0 <= rate <= 1.0

    def test_compute_failure_distribution(self):
        from forge.core.schemas import RunResult, RunStatus
        from forge.evaluation.metrics import compute_failure_distribution

        r1 = RunResult(run_id="r1", task_id="t1", agent_id="a1", status=RunStatus.COMPLETED)
        r1.passed = True
        results = [r1]
        dist = compute_failure_distribution(results)
        assert "success" in dist
        assert dist["success"] == 1


# ---------------------------------------------------------------------------
# Evaluation: Scoring
# ---------------------------------------------------------------------------


class TestScoring:
    def test_score_run(self):
        from forge.core.schemas import RunResult, RunStatus, VerificationResult
        from forge.evaluation.scoring import score_run

        result = RunResult(
            run_id="r1",
            task_id="t1",
            agent_id="a1",
            status=RunStatus.COMPLETED,
        )
        result.passed = True
        result.agent_made_changes = True
        result.verification = VerificationResult(
            run_id="r1",
            passed=True,
            existing_tests_passed=True,
        )
        score = score_run(result)
        assert 0.0 <= score <= 1.0

    def test_evaluation_report(self):
        from forge.core.schemas import RunResult, RunStatus
        from forge.evaluation.scoring import EvaluationReport

        r1 = RunResult(run_id="r1", task_id="t1", agent_id="a1", status=RunStatus.COMPLETED)
        r1.passed = True
        report = EvaluationReport(title="Test Report")
        report.generate([r1])
        assert report.data["summary"]["total_runs"] == 1


# ---------------------------------------------------------------------------
# Diagnosis: Rules
# ---------------------------------------------------------------------------


class TestDiagnosisRules:
    def test_get_all_rules(self):
        from forge.diagnosis.rules import get_all_rules

        rules = get_all_rules()
        assert len(rules) >= 5

    def test_evaluate_rules(self):
        from forge.core.schemas import RunResult, RunStatus
        from forge.diagnosis.rules import evaluate_rules

        result = RunResult(
            run_id="r1",
            task_id="t1",
            agent_id="a1",
            status=RunStatus.COMPLETED,
        )
        result.passed = False
        result.agent_made_changes = False
        evaluations = evaluate_rules(result)
        assert len(evaluations) >= 1


# ---------------------------------------------------------------------------
# Diagnosis: Triage
# ---------------------------------------------------------------------------


class TestTriage:
    def test_triage_run(self):
        from forge.core.schemas import RunResult, RunStatus
        from forge.diagnosis.triage import triage_run

        result = RunResult(
            run_id="r1",
            task_id="t1",
            agent_id="a1",
            status=RunStatus.COMPLETED,
        )
        result.passed = False
        result.agent_made_changes = False
        triage = triage_run(result)
        assert "primary_category" in triage
        assert "confidence" in triage


# ---------------------------------------------------------------------------
# Curriculum: Capability Tracker
# ---------------------------------------------------------------------------


class TestCapabilityTracker:
    def test_update_and_weakness(self):
        from forge.curriculum.capability_tracker import CapabilityTracker

        tracker = CapabilityTracker(capabilities=["debugging"])
        for _ in range(5):
            tracker.capabilities["debugging"].update(False, 2)

        weaknesses = tracker.get_weaknesses(threshold=0.4, min_attempts=3)
        assert "debugging" in weaknesses

    def test_confidence_estimate(self):
        from forge.curriculum.capability_tracker import CapabilityRecord

        record = CapabilityRecord("test")
        record.update(True)
        record.update(True)
        assert record.confidence_estimate > 0.5


# ---------------------------------------------------------------------------
# Curriculum: Difficulty
# ---------------------------------------------------------------------------


class TestDifficulty:
    def test_estimate_difficulty(self):
        from forge.curriculum.difficulty import estimate_difficulty

        diff = estimate_difficulty(["debugging", "testing"], "pagination_boundary")
        assert 1 <= diff <= 5

    def test_adjust_difficulty(self):
        from forge.curriculum.difficulty import adjust_difficulty

        assert adjust_difficulty(3, 0.9) == 4  # High success -> increase
        assert adjust_difficulty(3, 0.1) == 2  # Low success -> decrease

    def test_difficulty_label(self):
        from forge.curriculum.difficulty import get_difficulty_label

        assert get_difficulty_label(1) == "Trivial"
        assert get_difficulty_label(5) == "Expert"


# ---------------------------------------------------------------------------
# Curriculum: History
# ---------------------------------------------------------------------------


class TestCurriculumHistory:
    def test_record_and_query(self):
        from forge.curriculum.history import CurriculumHistory

        history = CurriculumHistory()
        history.record(1, "task-1", "adaptive", "Weakness: debugging")
        decisions = history.get_decisions_for_generation(1)
        assert len(decisions) == 1
        assert decisions[0].selected_task_id == "task-1"


# ---------------------------------------------------------------------------
# Experiments: Config
# ---------------------------------------------------------------------------


class TestExperimentConfig:
    def test_preset_experiments(self):
        from forge.experiments.config import get_preset_experiments

        presets = get_preset_experiments()
        assert "A" in presets
        assert "B" in presets
        assert "C" in presets
        assert "D" in presets


# ---------------------------------------------------------------------------
# Experiments: Artifacts
# ---------------------------------------------------------------------------


class TestArtifactManager:
    def test_store_and_list(self, tmp_path):
        from forge.core.schemas import RunResult, RunStatus
        from forge.experiments.artifacts import ArtifactManager

        manager = ArtifactManager(tmp_path / "artifacts")
        result = RunResult(
            run_id="r1",
            task_id="t1",
            agent_id="a1",
            status=RunStatus.COMPLETED,
        )
        result.passed = True
        manager.store_run_artifacts(result)
        artifacts = manager.list_artifacts()
        assert len(artifacts) == 1
        assert artifacts[0]["run_id"] == "r1"


# ---------------------------------------------------------------------------
# Sandbox: Policies
# ---------------------------------------------------------------------------


class TestSandboxPolicies:
    def test_default_policy(self):
        from forge.sandbox.policies import get_default_policy

        policy = get_default_policy()
        assert policy.network_disabled is True
        assert policy.non_root_user is True

    def test_docker_args(self):
        from forge.sandbox.policies import get_default_policy

        policy = get_default_policy()
        args = policy.to_docker_args()
        assert "--network=none" in args
        assert "--read-only" in args

    def test_strict_policy(self):
        from forge.sandbox.policies import get_strict_policy

        policy = get_strict_policy()
        assert policy.memory_limit == "256m"


# ---------------------------------------------------------------------------
# Task Factory: Mutations
# ---------------------------------------------------------------------------


class TestMutations:
    def test_get_all_mutations(self):
        from forge.task_factory.mutations import get_all_mutations

        mutations = get_all_mutations()
        assert len(mutations) >= 3

    def test_get_mutation_by_id(self):
        from forge.task_factory.mutations import get_mutation

        mutation = get_mutation("pagination_boundary")
        assert mutation is not None
        assert mutation.mutation_id == "pagination_boundary"

    def test_get_mutations_by_capability(self):
        from forge.task_factory.mutations import get_mutations_by_capability

        mutations = get_mutations_by_capability("debugging")
        assert len(mutations) >= 1


# ---------------------------------------------------------------------------
# Task Factory: Selection
# ---------------------------------------------------------------------------


class TestTaskPool:
    def test_add_and_select(self):
        from forge.task_factory.selection import TaskPool

        pool = TaskPool()
        pool.add_task("t1", {"difficulty_level": 2, "capabilities": ["debugging"]})
        pool.add_task("t2", {"difficulty_level": 3, "capabilities": ["testing"]})
        selected = pool.select_random(count=1)
        assert len(selected) == 1

    def test_select_by_capability(self):
        from forge.task_factory.selection import TaskPool

        pool = TaskPool()
        pool.add_task("t1", {"difficulty_level": 2, "capabilities": ["debugging"]})
        pool.add_task("t2", {"difficulty_level": 3, "capabilities": ["testing"]})
        selected = pool.select_by_capability("debugging", count=1)
        assert "t1" in selected

    def test_pool_stats(self):
        from forge.task_factory.selection import TaskPool

        pool = TaskPool()
        pool.add_task("t1", {"difficulty_level": 2})
        stats = pool.get_pool_stats()
        assert stats["total_tasks"] == 1


# ---------------------------------------------------------------------------
# Training: Adapter
# ---------------------------------------------------------------------------


class TestTrainingAdapter:
    def test_noop_adapter(self):
        from forge.training.adapter import NoOpTrainingAdapter

        adapter = NoOpTrainingAdapter()
        result = adapter.train([])
        assert result["adapter"] == "NoOpTrainingAdapter"

    def test_trajectory_exporter(self):
        from forge.core.schemas import RunResult, RunStatus, Trajectory, TrajectoryStep
        from forge.training.adapter import TrajectoryExporter

        traj = Trajectory(
            trajectory_id="traj-1",
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
        )
        traj.add_step(
            TrajectoryStep(
                step_index=0,
                observation="Start",
                action="read_file",
                tool_name="read_file",
            )
        )

        result = RunResult(
            run_id="run-1",
            task_id="task-1",
            agent_id="agent-1",
            status=RunStatus.COMPLETED,
        )
        result.passed = True
        result.trajectory = traj
        exporter = TrajectoryExporter()
        data = exporter.export_trajectory(result)
        assert data["final_outcome"]["passed"] is True
