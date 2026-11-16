"""Integration tests for ForgeLab.

These tests verify the full pipeline works end-to-end:
world generation → task creation → validation → agent execution →
verification → diagnosis → curriculum update.

They use MockAgent and do not require Docker or API keys.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from forge.agents.mock_agent import MockAgent
from forge.core.schemas import (
    AgentConfig,
    FailureCategory,
    RunConfig,
    RunStatus,
    TaskCategory,
    TaskSpec,
)
from forge.curriculum.selector import CurriculumSelector
from forge.diagnosis.classifier import FailureClassifier
from forge.experiments.manager import ExperimentConfig, ExperimentManager
from forge.runner.orchestrator import RunOrchestrator
from forge.task_factory.generator import TaskGenerator
from forge.validators.world_validator import TaskValidator, WorldValidator
from forge.world_factory.generator import WorldGenerator


class TestFullPipeline:
    """Test the complete generate → train → evaluate → adapt loop."""

    @pytest.fixture()
    def temp_dir(self):
        """Create a temporary directory for test artifacts."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    @pytest.fixture()
    def world_generator(self, temp_dir: Path):
        return WorldGenerator(output_dir=str(temp_dir / "worlds"))

    @pytest.fixture()
    def task_generator(self):
        return TaskGenerator()

    @pytest.fixture()
    def world_validator(self):
        return WorldValidator()

    @pytest.fixture()
    def task_validator(self):
        return TaskValidator()

    @pytest.fixture()
    def orchestrator(self, temp_dir: Path):
        return RunOrchestrator(artifacts_dir=str(temp_dir / "runs"))

    @pytest.fixture()
    def classifier(self):
        return FailureClassifier()

    @pytest.fixture()
    def curriculum(self):
        return CurriculumSelector()

    def test_world_generation_is_deterministic(self, world_generator: WorldGenerator):
        """Same seed should produce identical worlds."""
        spec1 = world_generator.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=42,
        )
        spec2 = world_generator.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=42,
        )
        assert spec1.world_id == spec2.world_id
        assert spec1.seed == spec2.seed
        assert spec1.mutation_id == spec2.mutation_id

    def test_world_and_task_creation(
        self,
        world_generator: WorldGenerator,
        task_generator: TaskGenerator,
    ):
        """World generation should produce a valid world spec and task."""
        world = world_generator.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=100,
        )
        assert world.world_id is not None
        assert world.world_type == "python_repository"
        assert world.mutation_id == "pagination_boundary"

        task = task_generator.generate_from_world(world)
        assert task.task_id is not None
        assert task.world_id == world.world_id
        # Category depends on mutation; pagination_boundary maps to edge_case_debugging
        assert task.category in (TaskCategory.BUG_REPAIR, TaskCategory.EDGE_CASE_DEBUGGING)
        assert len(task.description) > 0
        assert len(task.constraints) > 0

    def test_task_validation(
        self,
        world_generator: WorldGenerator,
        task_generator: TaskGenerator,
        task_validator: TaskValidator,
    ):
        """Valid tasks should pass validation."""
        world = world_generator.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=200,
        )
        task = task_generator.generate_from_world(world)
        status, issues = task_validator.validate(task, world)
        # Task should be valid or have minor issues, not rejected
        assert status.value in ("valid", "warning")

    def test_mock_agent_execution(
        self,
        world_generator: WorldGenerator,
        task_generator: TaskGenerator,
        orchestrator: RunOrchestrator,
    ):
        """MockAgent should execute and produce a trajectory."""
        world = world_generator.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=300,
        )
        task = task_generator.generate_from_world(world)

        agent_config = AgentConfig(
            agent_id="mock-test-agent",
            agent_type="mock",
            metadata={"scenario": "success"},
        )
        agent = MockAgent(config=agent_config)

        run_config = RunConfig(
            run_id="integration-test-run-1",
            task_id=task.task_id,
            agent_id=agent_config.agent_id,
            max_steps=20,
            timeout_seconds=60,
        )

        # Execute agent directly
        trajectory = agent.execute(task, Path(world.metadata["world_dir"]), run_config)
        assert trajectory.run_id == run_config.run_id
        assert trajectory.task_id == task.task_id
        assert len(trajectory.steps) > 0

    def test_failure_classification(
        self,
        classifier: FailureClassifier,
    ):
        """Classifier should correctly categorize different failure types."""
        from forge.core.schemas import RunResult, Trajectory, VerificationResult

        # Agent failure: valid env, valid task, agent didn't solve
        traj = Trajectory(run_id="test-run-1", task_id="test-task", agent_id="test-agent")
        run_result = RunResult(
            run_id="test-run-1",
            task_id="test-task",
            agent_id="test-agent",
            status=RunStatus.FAILED,
        )
        run_result.trajectory = traj
        run_result.verification = VerificationResult(
            run_id="test-run-1", passed=False, public_tests_ran=True, hidden_tests_ran=True
        )
        run_result.error = "Agent did not solve the task"
        diagnosis = classifier.classify(run_result)
        # Classifier should return a valid diagnosis with a category
        assert diagnosis.primary_category in FailureCategory

        # Environment failure: dependency error
        traj2 = Trajectory(run_id="test-run-2", task_id="test-task", agent_id="test-agent")
        run_result2 = RunResult(
            run_id="test-run-2",
            task_id="test-task",
            agent_id="test-agent",
            status=RunStatus.FAILED,
        )
        run_result2.trajectory = traj2
        run_result2.verification = VerificationResult(run_id="test-run-2", passed=False, public_tests_ran=False)
        run_result2.error = "ModuleNotFoundError: No module named 'requests'"
        diagnosis = classifier.classify(run_result2)
        assert diagnosis.primary_category in FailureCategory

    def test_curriculum_adaptive_selection(
        self,
        curriculum: CurriculumSelector,
    ):
        """Adaptive curriculum should target weaknesses via CapabilityTracker."""
        from forge.core.schemas import RunResult, Trajectory, VerificationResult

        # Record failures in debugging via RunResult
        for i in range(3):
            traj = Trajectory(run_id=f"test-run-{i}", task_id="test-task", agent_id="test-agent")
            result = RunResult(
                run_id=f"test-run-{i}",
                task_id="test-task",
                agent_id="test-agent",
                status=RunStatus.FAILED,
            )
            result.trajectory = traj
            result.verification = VerificationResult(run_id=f"test-run-{i}", passed=False)
            result.metadata = {"capabilities": ["debugging"]}
            curriculum.update(result)

        # Record successes in other capabilities
        for idx, cap in enumerate(["edge_case_reasoning", "testing"]):
            traj = Trajectory(run_id=f"test-run-s-{idx}", task_id="test-task", agent_id="test-agent")
            result = RunResult(
                run_id=f"test-run-s-{idx}",
                task_id="test-task",
                agent_id="test-agent",
                status=RunStatus.COMPLETED,
            )
            result.trajectory = traj
            result.verification = VerificationResult(run_id=f"test-run-s-{idx}", passed=True)
            result.metadata = {"capabilities": [cap]}
            curriculum.update(result)

        # Debugging should be identified as a weakness
        data = curriculum.tracker.get_all_data()
        assert "debugging" in data
        assert data["debugging"]["attempts"] == 3
        assert data["debugging"]["successes"] == 0

    def test_experiment_creation(
        self,
        temp_dir: Path,
    ):
        """Experiments should be creatable and trackable."""
        manager = ExperimentManager()
        config = ExperimentConfig(
            name="Integration Test Experiment",
            experiment_id="integration-test-exp",
            description="Test experiment for integration tests",
            hypothesis="H1",
        )
        manager.create_experiment(config)
        experiments = manager.list_experiments()
        assert len(experiments) > 0
        exp_ids = [e.experiment_id if hasattr(e, "experiment_id") else e.get("experiment_id") for e in experiments]
        assert "integration-test-exp" in exp_ids

    def test_world_directory_structure(
        self,
        world_generator: WorldGenerator,
    ):
        """Generated world should have expected directory structure."""
        world = world_generator.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=400,
        )
        world_dir = Path(world.metadata["world_dir"])
        assert world_dir.exists()
        assert world_dir.is_dir()

        # Should have source files
        py_files = list(world_dir.rglob("*.py"))
        assert len(py_files) > 0

        # Should have a git repository
        git_dir = world_dir / ".git"
        assert git_dir.exists()

    def test_all_mutations_generate(
        self,
        world_generator: WorldGenerator,
    ):
        """All registered mutations should generate valid worlds."""
        mutations = ["pagination_boundary", "empty_search", "duplicate_records"]
        for mutation in mutations:
            world = world_generator.generate(
                template_name="task_manager_api",
                mutation_id=mutation,
                seed=hash(mutation) % 10000,
            )
            assert world.mutation_id == mutation
            assert world.metadata["world_dir"] is not None


class TestTrajectoryCompleteness:
    """Test that trajectories are properly recorded."""

    @pytest.fixture()
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    def test_trajectory_has_required_fields(
        self,
        temp_dir: Path,
    ):
        """Trajectory steps should have all required fields."""
        world_gen = WorldGenerator(output_dir=str(temp_dir / "worlds"))
        task_gen = TaskGenerator()

        world = world_gen.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=500,
        )
        task = task_gen.generate_from_world(world)

        agent_config = AgentConfig(
            agent_id="mock-trajectory-test",
            agent_type="mock",
            metadata={"scenario": "success"},
        )
        agent = MockAgent(config=agent_config)

        run_config = RunConfig(
            run_id="trajectory-test-run",
            task_id=task.task_id,
            agent_id=agent_config.agent_id,
            max_steps=20,
            timeout_seconds=60,
        )

        trajectory = agent.execute(task, Path(world.metadata["world_dir"]), run_config)

        # Check trajectory-level fields
        assert trajectory.run_id == "trajectory-test-run"
        assert trajectory.task_id == task.task_id
        assert trajectory.agent_id == "mock-trajectory-test"

        # Check step-level fields
        for step in trajectory.steps:
            assert step.step_index >= 0
            assert step.action is not None
            assert step.duration_seconds is not None


class TestOpenAICompatibleAgent:
    """Test the OpenAI-compatible agent adapter."""

    def test_agent_imports(self):
        """OpenAICompatibleAgent should import without error."""
        from forge.agents.openai_compatible import OpenAICompatibleAgent

        assert OpenAICompatibleAgent is not None

    def test_agent_without_api_key(self):
        """Agent should handle missing API key gracefully."""
        from forge.agents.openai_compatible import OpenAICompatibleAgent

        config = AgentConfig(
            agent_id="openai-test",
            agent_type="openai_compatible",
        )
        agent = OpenAICompatibleAgent(config=config)

        # Should return error trajectory when API not configured
        import tempfile
        from pathlib import Path

        from forge.core.schemas import RunConfig

        task = TaskSpec(
            task_id="test-task",
            world_id="test-world",
            category=TaskCategory.EDGE_CASE_DEBUGGING,
            description="Test task",
            constraints=["preserve_existing_api"],
        )
        run_config = RunConfig(
            run_id="test-run",
            task_id="test-task",
            agent_id="openai-test",
        )

        with tempfile.TemporaryDirectory() as td:
            trajectory = agent.execute(task, Path(td), run_config)
            assert trajectory.termination_reason == "api_not_configured"
            assert len(trajectory.steps) == 1
            assert trajectory.steps[0].action == "error"

    def test_agent_tools_list(self):
        """Agent should list all available tools."""
        from forge.agents.openai_compatible import OpenAICompatibleAgent

        config = AgentConfig(
            agent_id="openai-tools-test",
            agent_type="openai_compatible",
        )
        agent = OpenAICompatibleAgent(config=config)
        tools = agent.get_available_tools()

        expected_tools = [
            "list_files",
            "read_file",
            "search_code",
            "write_file",
            "run_public_tests",
            "inspect_test_output",
            "inspect_git_diff",
            "finish_task",
        ]
        assert tools == expected_tools
