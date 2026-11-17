"""Unit tests for ForgeLab core modules.

Tests schemas, config, registry, events, and errors.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from forge.core.config import Config
from forge.core.errors import (
    AgentExecutionError,
    ForgeLabError,
    SandboxError,
    TaskValidationError,
    WorldGenerationError,
)
from forge.core.events import Event, EventEmitter, EventType
from forge.core.registry import Registry
from forge.core.schemas import (
    AgentConfig,
    CurriculumState,
    CurriculumStrategy,
    ExperimentConfig,
    FailureCategory,
    FailureDiagnosis,
    RunConfig,
    RunResult,
    RunStatus,
    TaskCategory,
    TaskSpec,
    Trajectory,
    TrajectoryStep,
    ValidationStatus,
    VerificationResult,
    WorldSpec,
    generate_id,
)

# ---------------------------------------------------------------------------
# ID Generation
# ---------------------------------------------------------------------------


class TestGenerateId:
    def test_generate_id_no_prefix(self):
        uid = generate_id()
        assert len(uid) == 12
        assert uid.isalnum()

    def test_generate_id_with_prefix(self):
        uid = generate_id("world-")
        assert uid.startswith("world-")
        assert len(uid) == 18  # "world-" (6) + 12 hex chars

    def test_generate_id_uniqueness(self):
        ids = {generate_id("test-") for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_task_category_values(self):
        assert TaskCategory.BUG_REPAIR.value == "bug_repair"
        assert TaskCategory.EDGE_CASE_DEBUGGING.value == "edge_case_debugging"
        assert TaskCategory.REGRESSION_REPAIR.value == "regression_repair"

    def test_failure_category_values(self):
        assert FailureCategory.AGENT_FAILURE.value == "agent_failure"
        assert FailureCategory.ENVIRONMENT_FAILURE.value == "environment_failure"
        assert FailureCategory.UNCERTAIN.value == "uncertain"

    def test_run_status_values(self):
        assert RunStatus.PENDING.value == "pending"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.TIMED_OUT.value == "timed_out"

    def test_validation_status_values(self):
        assert ValidationStatus.VALID.value == "valid"
        assert ValidationStatus.QUARANTINED.value == "quarantined"

    def test_curriculum_strategy_values(self):
        assert CurriculumStrategy.STATIC.value == "static"
        assert CurriculumStrategy.ADAPTIVE.value == "adaptive"


# ---------------------------------------------------------------------------
# WorldSpec
# ---------------------------------------------------------------------------


class TestWorldSpec:
    def test_create_world_spec(self):
        spec = WorldSpec(
            world_type="python_repository",
            template_name="task_manager_api",
            seed=42,
        )
        assert spec.world_id.startswith("world-")
        assert spec.schema_version == "1.0"
        assert spec.world_type == "python_repository"
        assert spec.seed == 42
        assert spec.created_at is not None

    def test_world_spec_to_dict(self):
        spec = WorldSpec(
            world_type="python_repository",
            template_name="test",
            seed=1,
        )
        d = spec.to_dict()
        assert d["world_id"] == spec.world_id
        assert d["seed"] == 1
        assert d["world_type"] == "python_repository"

    def test_world_spec_from_dict(self):
        data = {
            "world_id": "world-abc123",
            "world_type": "python_repository",
            "template_name": "test",
            "seed": 42,
            "dependencies": ["pytest"],
        }
        spec = WorldSpec.from_dict(data)
        assert spec.world_id == "world-abc123"
        assert spec.seed == 42
        assert spec.dependencies == ["pytest"]

    def test_world_spec_round_trip(self):
        spec = WorldSpec(
            world_type="python_repository",
            template_name="test",
            seed=99,
            mutation_id="mut-1",
        )
        restored = WorldSpec.from_dict(spec.to_dict())
        assert restored.world_id == spec.world_id
        assert restored.seed == spec.seed
        assert restored.mutation_id == spec.mutation_id


# ---------------------------------------------------------------------------
# TaskSpec
# ---------------------------------------------------------------------------


class TestTaskSpec:
    def test_create_task_spec(self):
        spec = TaskSpec(
            world_id="world-123",
            category=TaskCategory.BUG_REPAIR,
            description="Fix pagination bug",
            difficulty_level=2,
            capabilities=["debugging", "edge_case_reasoning"],
        )
        assert spec.task_id.startswith("task-")
        assert spec.category == TaskCategory.BUG_REPAIR
        assert spec.difficulty_level == 2

    def test_task_spec_to_dict(self):
        spec = TaskSpec(
            world_id="world-123",
            category=TaskCategory.BUG_REPAIR,
            description="Fix bug",
        )
        d = spec.to_dict()
        assert d["category"] == "bug_repair"
        assert d["world_id"] == "world-123"

    def test_task_spec_from_dict(self):
        data = {
            "task_id": "task-abc",
            "world_id": "world-123",
            "category": "bug_repair",
            "description": "Fix bug",
            "difficulty_level": 3,
        }
        spec = TaskSpec.from_dict(data)
        assert spec.task_id == "task-abc"
        assert spec.category == TaskCategory.BUG_REPAIR
        assert spec.difficulty_level == 3

    def test_task_spec_round_trip(self):
        spec = TaskSpec(
            world_id="world-123",
            category=TaskCategory.EDGE_CASE_DEBUGGING,
            description="Fix edge case",
            constraints=["preserve_existing_api"],
            capabilities=["testing"],
        )
        restored = TaskSpec.from_dict(spec.to_dict())
        assert restored.task_id == spec.task_id
        assert restored.constraints == spec.constraints
        assert restored.capabilities == spec.capabilities


# ---------------------------------------------------------------------------
# AgentConfig
# ---------------------------------------------------------------------------


class TestAgentConfig:
    def test_create_agent_config(self):
        config = AgentConfig(
            agent_type="mock",
            max_steps=30,
        )
        assert config.agent_id.startswith("agent-")
        assert config.agent_type == "mock"
        assert config.max_steps == 30

    def test_agent_config_round_trip(self):
        config = AgentConfig(
            agent_type="openai_compatible",
            model="gpt-4",
            provider="openai",
            tools=["read_file", "write_file"],
        )
        restored = AgentConfig.from_dict(config.to_dict())
        assert restored.model == config.model
        assert restored.tools == config.tools


# ---------------------------------------------------------------------------
# RunConfig
# ---------------------------------------------------------------------------


class TestRunConfig:
    def test_create_run_config(self):
        config = RunConfig(
            task_id="task-123",
            agent_id="agent-456",
            seed=42,
        )
        assert config.run_id.startswith("run-")
        assert config.seed == 42

    def test_run_config_round_trip(self):
        config = RunConfig(
            task_id="task-123",
            agent_id="agent-456",
            experiment_id="exp-789",
        )
        restored = RunConfig.from_dict(config.to_dict())
        assert restored.experiment_id == "exp-789"


# ---------------------------------------------------------------------------
# Trajectory
# ---------------------------------------------------------------------------


class TestTrajectory:
    def test_create_trajectory(self):
        traj = Trajectory(
            run_id="run-123",
            task_id="task-456",
            agent_id="agent-789",
        )
        assert traj.trajectory_id.startswith("traj-")
        assert traj.steps == []

    def test_add_step(self):
        traj = Trajectory("run-1", "task-1", "agent-1")
        step = TrajectoryStep(
            step_index=0,
            observation="Initial state",
            action="read_file",
            tool_name="read_file",
            tool_arguments={"path": "main.py"},
        )
        traj.add_step(step)
        assert len(traj.steps) == 1
        assert traj.steps[0].tool_name == "read_file"

    def test_finalize(self):
        traj = Trajectory("run-1", "task-1", "agent-1")
        traj.finalize("completed", 10.5, {"prompt": 100, "completion": 50})
        assert traj.termination_reason == "completed"
        assert traj.total_duration_seconds == 10.5
        assert traj.finished_at is not None

    def test_trajectory_round_trip(self):
        traj = Trajectory("run-1", "task-1", "agent-1")
        traj.add_step(TrajectoryStep(step_index=0, tool_name="read_file"))
        traj.finalize("completed", 5.0)
        restored = Trajectory.from_dict(traj.to_dict())
        assert len(restored.steps) == 1
        assert restored.termination_reason == "completed"


# ---------------------------------------------------------------------------
# VerificationResult
# ---------------------------------------------------------------------------


class TestVerificationResult:
    def test_create_verification_result(self):
        result = VerificationResult(
            run_id="run-123",
            passed=True,
            hidden_tests_passed=True,
            score=1.0,
        )
        assert result.verification_id.startswith("verif-")
        assert result.passed is True

    def test_verification_round_trip(self):
        result = VerificationResult(
            run_id="run-123",
            passed=False,
            test_results={"test_a": True, "test_b": False},
            details="test_b failed",
        )
        restored = VerificationResult.from_dict(result.to_dict())
        assert restored.test_results == {"test_a": True, "test_b": False}
        assert restored.details == "test_b failed"


# ---------------------------------------------------------------------------
# FailureDiagnosis
# ---------------------------------------------------------------------------


class TestFailureDiagnosis:
    def test_create_diagnosis(self):
        diag = FailureDiagnosis(
            run_id="run-123",
            primary_category=FailureCategory.AGENT_FAILURE,
            supporting_evidence=["Agent did not fix the bug"],
            confidence=0.9,
        )
        assert diag.diagnosis_id.startswith("diag-")
        assert diag.primary_category == FailureCategory.AGENT_FAILURE

    def test_diagnosis_round_trip(self):
        diag = FailureDiagnosis(
            run_id="run-123",
            primary_category=FailureCategory.ENVIRONMENT_FAILURE,
            supporting_evidence=["Docker failed"],
            contradictory_evidence=["Other runs succeeded"],
        )
        restored = FailureDiagnosis.from_dict(diag.to_dict())
        assert restored.primary_category == FailureCategory.ENVIRONMENT_FAILURE
        assert len(restored.supporting_evidence) == 1


# ---------------------------------------------------------------------------
# RunResult
# ---------------------------------------------------------------------------


class TestRunResult:
    def test_create_run_result(self):
        result = RunResult(
            run_id="run-123",
            task_id="task-456",
            agent_id="agent-789",
            status=RunStatus.COMPLETED,
        )
        assert result.result_id.startswith("result-")
        assert result.status == RunStatus.COMPLETED

    def test_run_result_with_verification(self):
        result = RunResult("run-1", "task-1", "agent-1")
        result.verification = VerificationResult("run-1", passed=True)
        result.diagnosis = FailureDiagnosis("run-1", FailureCategory.AGENT_FAILURE)
        d = result.to_dict()
        assert d["verification"]["passed"] is True
        assert d["diagnosis"]["primary_category"] == "agent_failure"

    def test_run_result_round_trip(self):
        result = RunResult("run-1", "task-1", "agent-1", status=RunStatus.FAILED)
        result.verification = VerificationResult("run-1", passed=False)
        restored = RunResult.from_dict(result.to_dict())
        assert restored.status == RunStatus.FAILED
        assert restored.verification.passed is False


# ---------------------------------------------------------------------------
# CurriculumState
# ---------------------------------------------------------------------------


class TestCurriculumState:
    def test_create_curriculum_state(self):
        state = CurriculumState(
            strategy=CurriculumStrategy.ADAPTIVE,
            capability_scores={"debugging": 0.7, "testing": 0.3},
        )
        assert state.curriculum_id.startswith("curr-")
        assert state.strategy == CurriculumStrategy.ADAPTIVE

    def test_curriculum_round_trip(self):
        state = CurriculumState(
            strategy=CurriculumStrategy.RANDOM,
            task_pool=["task-1", "task-2"],
            generation=5,
        )
        restored = CurriculumState.from_dict(state.to_dict())
        assert restored.strategy == CurriculumStrategy.RANDOM
        assert restored.generation == 5


# ---------------------------------------------------------------------------
# ExperimentConfig
# ---------------------------------------------------------------------------


class TestExperimentConfig:
    def test_create_experiment_config(self):
        config = ExperimentConfig(
            name="Static vs Adaptive",
            hypothesis="Adaptive curriculum improves performance",
            random_seed=42,
        )
        assert config.experiment_id.startswith("exp-")
        assert config.random_seed == 42

    def test_experiment_round_trip(self):
        config = ExperimentConfig(
            name="Test",
            task_selection_strategy=CurriculumStrategy.ADAPTIVE,
            model_identifier="gpt-4",
        )
        restored = ExperimentConfig.from_dict(config.to_dict())
        assert restored.model_identifier == "gpt-4"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_default_config(self):
        config = Config()
        # Database URL may be overridden by FORGELAB_DATABASE_URL env var (e.g. Vercel)
        db_url = config.get("database.url")
        assert db_url.startswith("sqlite:///")
        assert config.get("sandbox.network_disabled") is True

    def test_config_get_with_default(self):
        config = Config()
        assert config.get("nonexistent.key", "default") == "default"

    def test_config_get_section(self):
        config = Config()
        section = config.get_section("sandbox")
        assert isinstance(section, dict)
        assert "image" in section

    def test_config_yaml_override(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            yaml_file = config_dir / "override.yaml"
            yaml_file.write_text("database:\n  echo: true\n")
            config = Config(config_dir=str(config_dir))
            assert config.get("database.echo") is True

    def test_config_env_override(self):
        os.environ["FORGELAB_LOG_LEVEL"] = "DEBUG"
        try:
            config = Config()
            assert config.get("logging.level") == "DEBUG"
        finally:
            del os.environ["FORGELAB_LOG_LEVEL"]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_register_and_get(self):
        reg = Registry("test")
        reg.register("item1", {"value": 1})
        assert reg.get("item1") == {"value": 1}

    def test_exists(self):
        reg = Registry("test")
        reg.register("item1", "data")
        assert reg.exists("item1")
        assert not reg.exists("missing")

    def test_list_all(self):
        reg = Registry("test")
        reg.register("b", 1)
        reg.register("a", 2)
        assert reg.list_all() == ["a", "b"]

    def test_filter_by_tag(self):
        reg = Registry("test")
        reg.register("a", 1, metadata={"type": "mock"})
        reg.register("b", 2, metadata={"type": "real"})
        assert reg.filter_by_tag("type", "mock") == ["a"]

    def test_unregister(self):
        reg = Registry("test")
        reg.register("item1", "data")
        assert reg.unregister("item1") is True
        assert not reg.exists("item1")

    def test_contains(self):
        reg = Registry("test")
        reg.register("item1", "data")
        assert "item1" in reg
        assert "missing" not in reg

    def test_len(self):
        reg = Registry("test")
        reg.register("a", 1)
        reg.register("b", 2)
        assert len(reg) == 2


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class TestEvents:
    def test_event_creation(self):
        event = Event(EventType.RUN_STARTED, source="orchestrator")
        assert event.event_type == EventType.RUN_STARTED
        assert event.timestamp is not None
        assert event.event_id is not None

    def test_event_to_dict(self):
        event = Event(EventType.RUN_COMPLETED, source="test", data={"score": 0.9})
        d = event.to_dict()
        assert d["event_type"] == "run.completed"
        assert d["data"]["score"] == 0.9

    def test_event_emitter(self):
        emitter = EventEmitter()
        received = []

        def handler(event):
            received.append(event)

        emitter.on(EventType.RUN_STARTED, handler)
        emitter.emit(Event(EventType.RUN_STARTED, source="test"))
        assert len(received) == 1

    def test_event_history(self):
        emitter = EventEmitter()
        emitter.emit(Event(EventType.RUN_STARTED, source="test"))
        emitter.emit(Event(EventType.RUN_COMPLETED, source="test"))
        assert len(emitter.get_history()) == 2
        assert len(emitter.get_history(EventType.RUN_STARTED)) == 1

    def test_clear_history(self):
        emitter = EventEmitter()
        emitter.emit(Event(EventType.RUN_STARTED, source="test"))
        emitter.clear_history()
        assert len(emitter.get_history()) == 0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestErrors:
    def test_base_error(self):
        err = ForgeLabError("test message")
        assert str(err) == "test message"
        assert err.details == {}

    def test_error_with_details(self):
        err = ForgeLabError("test", details={"key": "value"})
        assert err.details["key"] == "value"

    def test_world_error_hierarchy(self):
        err = WorldGenerationError("gen failed")
        assert isinstance(err, ForgeLabError)
        assert isinstance(err, WorldGenerationError)

    def test_task_error_hierarchy(self):
        err = TaskValidationError("invalid")
        assert isinstance(err, ForgeLabError)

    def test_agent_error_hierarchy(self):
        err = AgentExecutionError("crash")
        assert isinstance(err, ForgeLabError)

    def test_sandbox_error_hierarchy(self):
        err = SandboxError("docker down")
        assert isinstance(err, ForgeLabError)
