"""Core data schemas for ForgeLab.

All persistent and API-facing data structures use Pydantic v2 models
for validation, serialization, and documentation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_id(prefix: str = "") -> str:
    """Generate a stable, short identifier."""
    uid = uuid4().hex[:12]
    return f"{prefix}{uid}" if prefix else uid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskCategory(str, Enum):
    """Categories of software engineering tasks."""

    BUG_REPAIR = "bug_repair"
    EDGE_CASE_DEBUGGING = "edge_case_debugging"
    REGRESSION_REPAIR = "regression_repair"
    FEATURE_IMPLEMENTATION = "feature_implementation"
    TEST_DRIVEN_DEBUGGING = "test_driven_debugging"


class FailureCategory(str, Enum):
    """Diagnosed cause of a failed run."""

    AGENT_FAILURE = "agent_failure"
    ENVIRONMENT_FAILURE = "environment_failure"
    INVALID_TASK = "invalid_task"
    VERIFIER_FAILURE = "verifier_failure"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    UNCERTAIN = "uncertain"


class RunStatus(str, Enum):
    """Lifecycle status of an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ValidationStatus(str, Enum):
    """Validation state of a world or task."""

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    QUARANTINED = "quarantined"


class CurriculumStrategy(str, Enum):
    """Task selection strategies for the curriculum engine."""

    STATIC = "static"
    RANDOM = "random"
    ADAPTIVE = "adaptive"


# ---------------------------------------------------------------------------
# World Specification
# ---------------------------------------------------------------------------


class WorldSpec:
    """Specification for an executable software environment.

    A world is a reproducible, isolated software repository that an agent
    can interact with.  It contains the source code, dependencies, and
    initial state needed for a task.

    Attributes:
        world_id: Unique identifier for this world.
        schema_version: Version of this spec format.
        world_type: Type of environment (e.g. "python_repository").
        template_name: Name of the template used to generate this world.
        template_version: Version of the template.
        seed: Random seed for deterministic generation.
        initial_commit: Git commit hash of the initial (broken) state.
        mutation_id: Identifier of the injected defect/mutation.
        dependencies: List of dependency specifications.
        metadata: Arbitrary key-value metadata.
        created_at: Timestamp of creation.
    """

    def __init__(
        self,
        world_type: str,
        template_name: str,
        template_version: str = "0.1",
        seed: int | None = None,
        mutation_id: str | None = None,
        initial_commit: str | None = None,
        dependencies: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        world_id: str | None = None,
    ):
        self.world_id = world_id or generate_id("world-")
        self.schema_version = "1.0"
        self.world_type = world_type
        self.template_name = template_name
        self.template_version = template_version
        self.seed = seed
        self.initial_commit = initial_commit
        self.mutation_id = mutation_id
        self.dependencies = dependencies or []
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "schema_version": self.schema_version,
            "world_type": self.world_type,
            "template_name": self.template_name,
            "template_version": self.template_version,
            "seed": self.seed,
            "initial_commit": self.initial_commit,
            "mutation_id": self.mutation_id,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorldSpec:
        return cls(
            world_id=data.get("world_id"),
            world_type=data["world_type"],
            template_name=data["template_name"],
            template_version=data.get("template_version", "0.1"),
            seed=data.get("seed"),
            mutation_id=data.get("mutation_id"),
            initial_commit=data.get("initial_commit"),
            dependencies=data.get("dependencies", []),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Task Specification
# ---------------------------------------------------------------------------


class TaskSpec:
    """Structured specification for a software engineering task.

    A task spec defines what the agent should do inside a world,
    including the objective, constraints, verification method, and
    difficulty estimation.

    Attributes:
        task_id: Unique identifier for this task.
        schema_version: Version of this spec format.
        world_id: The world this task operates on.
        category: Category of the task.
        description: Human-readable task description for the agent.
        constraints: List of constraint identifiers.
        timeout_seconds: Maximum execution time.
        reset_after_run: Whether to reset the environment after a run.
        verification_method: How the result is verified.
        require_existing_tests: Whether existing tests must still pass.
        require_new_tests: Whether the agent must write new tests.
        difficulty_level: Estimated difficulty (1-5).
        capabilities: List of capability categories this task exercises.
        metadata: Arbitrary key-value metadata.
        created_at: Timestamp of creation.
    """

    def __init__(
        self,
        world_id: str,
        category: TaskCategory,
        description: str,
        task_id: str | None = None,
        constraints: list[str] | None = None,
        timeout_seconds: int = 300,
        reset_after_run: bool = True,
        verification_method: str = "isolated_hidden_pytest",
        require_existing_tests: bool = True,
        require_new_tests: bool = False,
        difficulty_level: int = 2,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.task_id = task_id or generate_id("task-")
        self.schema_version = "1.0"
        self.world_id = world_id
        self.category = category
        self.description = description
        self.constraints = constraints or []
        self.timeout_seconds = timeout_seconds
        self.reset_after_run = reset_after_run
        self.verification_method = verification_method
        self.require_existing_tests = require_existing_tests
        self.require_new_tests = require_new_tests
        self.difficulty_level = difficulty_level
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "schema_version": self.schema_version,
            "world_id": self.world_id,
            "category": self.category.value if isinstance(self.category, TaskCategory) else self.category,
            "description": self.description,
            "constraints": self.constraints,
            "timeout_seconds": self.timeout_seconds,
            "reset_after_run": self.reset_after_run,
            "verification_method": self.verification_method,
            "require_existing_tests": self.require_existing_tests,
            "require_new_tests": self.require_new_tests,
            "difficulty_level": self.difficulty_level,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskSpec:
        category = data.get("category")
        if isinstance(category, str):
            try:
                category = TaskCategory(category)
            except ValueError:
                pass
        return cls(
            task_id=data.get("task_id"),
            world_id=data["world_id"],
            category=category,
            description=data["description"],
            constraints=data.get("constraints", []),
            timeout_seconds=data.get("timeout_seconds", 300),
            reset_after_run=data.get("reset_after_run", True),
            verification_method=data.get("verification_method", "isolated_hidden_pytest"),
            require_existing_tests=data.get("require_existing_tests", True),
            require_new_tests=data.get("require_new_tests", False),
            difficulty_level=data.get("difficulty_level", 2),
            capabilities=data.get("capabilities", []),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Agent Configuration
# ---------------------------------------------------------------------------


class AgentConfig:
    """Configuration for an agent instance.

    Attributes:
        agent_id: Unique identifier for this agent.
        agent_type: Type of agent (e.g. "mock", "openai_compatible").
        model: Model identifier (for LLM agents).
        provider: API provider name.
        max_steps: Maximum tool-call steps per run.
        temperature: Sampling temperature.
        system_prompt: System prompt / instructions.
        tools: List of available tool names.
        metadata: Arbitrary key-value metadata.
    """

    def __init__(
        self,
        agent_type: str,
        agent_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        max_steps: int = 50,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        tools: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.agent_id = agent_id or generate_id("agent-")
        self.agent_type = agent_type
        self.model = model
        self.provider = provider
        self.max_steps = max_steps
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "model": self.model,
            "provider": self.provider,
            "max_steps": self.max_steps,
            "temperature": self.temperature,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        return cls(
            agent_id=data.get("agent_id"),
            agent_type=data["agent_type"],
            model=data.get("model"),
            provider=data.get("provider"),
            max_steps=data.get("max_steps", 50),
            temperature=data.get("temperature", 0.7),
            system_prompt=data.get("system_prompt"),
            tools=data.get("tools", []),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Run Configuration
# ---------------------------------------------------------------------------


class RunConfig:
    """Configuration for a single agent run.

    Attributes:
        run_id: Unique identifier for this run.
        task_id: The task being attempted.
        agent_id: The agent executing the task.
        experiment_id: Optional parent experiment.
        seed: Random seed for reproducibility.
        timeout_seconds: Maximum wall-clock time.
        max_steps: Maximum tool-call steps.
        sandbox_image: Docker image for sandbox execution.
        metadata: Arbitrary key-value metadata.
    """

    def __init__(
        self,
        task_id: str,
        agent_id: str,
        run_id: str | None = None,
        experiment_id: str | None = None,
        seed: int | None = None,
        timeout_seconds: int = 300,
        max_steps: int = 50,
        sandbox_image: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.run_id = run_id or generate_id("run-")
        self.task_id = task_id
        self.agent_id = agent_id
        self.experiment_id = experiment_id
        self.seed = seed
        self.timeout_seconds = timeout_seconds
        self.max_steps = max_steps
        self.sandbox_image = sandbox_image
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "experiment_id": self.experiment_id,
            "seed": self.seed,
            "timeout_seconds": self.timeout_seconds,
            "max_steps": self.max_steps,
            "sandbox_image": self.sandbox_image,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunConfig:
        return cls(
            run_id=data.get("run_id"),
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            experiment_id=data.get("experiment_id"),
            seed=data.get("seed"),
            timeout_seconds=data.get("timeout_seconds", 300),
            max_steps=data.get("max_steps", 50),
            sandbox_image=data.get("sandbox_image"),
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Trajectory
# ---------------------------------------------------------------------------


class TrajectoryStep:
    """A single step in an agent's execution trajectory.

    Attributes:
        step_index: Ordinal position in the trajectory.
        observation: What the agent observed before acting.
        action: The action / tool call chosen by the agent.
        tool_name: Name of the tool invoked (if any).
        tool_arguments: Arguments passed to the tool.
        tool_result: Output returned by the tool.
        duration_seconds: Time taken for this step.
        error: Error message if the step failed.
        metadata: Additional data (e.g. token usage).
    """

    def __init__(
        self,
        step_index: int,
        observation: str = "",
        action: str = "",
        tool_name: str | None = None,
        tool_arguments: dict[str, Any] | None = None,
        tool_result: str | None = None,
        duration_seconds: float = 0.0,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.step_index = step_index
        self.observation = observation
        self.action = action
        self.tool_name = tool_name
        self.tool_arguments = tool_arguments or {}
        self.tool_result = tool_result
        self.duration_seconds = duration_seconds
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "observation": self.observation,
            "action": self.action,
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments,
            "tool_result": self.tool_result,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrajectoryStep:
        return cls(
            step_index=data["step_index"],
            observation=data.get("observation", ""),
            action=data.get("action", ""),
            tool_name=data.get("tool_name"),
            tool_arguments=data.get("tool_arguments", {}),
            tool_result=data.get("tool_result"),
            duration_seconds=data.get("duration_seconds", 0.0),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


class Trajectory:
    """Complete execution trajectory for one agent run.

    Attributes:
        run_id: The run this trajectory belongs to.
        task_id: The task being attempted.
        agent_id: The agent that executed.
        steps: Ordered list of trajectory steps.
        started_at: Timestamp when execution began.
        finished_at: Timestamp when execution ended.
        termination_reason: Why execution stopped.
        total_duration_seconds: Wall-clock duration.
        total_token_usage: Token counts (for LLM agents).
    """

    def __init__(
        self,
        run_id: str,
        task_id: str,
        agent_id: str,
        trajectory_id: str | None = None,
    ):
        self.trajectory_id = trajectory_id or generate_id("traj-")
        self.run_id = run_id
        self.task_id = task_id
        self.agent_id = agent_id
        self.steps: list[TrajectoryStep] = []
        self.started_at = datetime.utcnow().isoformat()
        self.finished_at: str | None = None
        self.termination_reason: str | None = None
        self.total_duration_seconds: float = 0.0
        self.total_token_usage: dict[str, int] = {}

    def add_step(self, step: TrajectoryStep) -> None:
        self.steps.append(step)

    def finalize(
        self,
        termination_reason: str,
        total_duration_seconds: float,
        total_token_usage: dict[str, int] | None = None,
    ) -> None:
        self.finished_at = datetime.utcnow().isoformat()
        self.termination_reason = termination_reason
        self.total_duration_seconds = total_duration_seconds
        self.total_token_usage = total_token_usage or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "steps": [s.to_dict() for s in self.steps],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "termination_reason": self.termination_reason,
            "total_duration_seconds": self.total_duration_seconds,
            "total_token_usage": self.total_token_usage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trajectory:
        traj = cls(
            trajectory_id=data.get("trajectory_id"),
            run_id=data["run_id"],
            task_id=data["task_id"],
            agent_id=data["agent_id"],
        )
        for step_data in data.get("steps", []):
            traj.add_step(TrajectoryStep.from_dict(step_data))
        traj.started_at = data.get("started_at", traj.started_at)
        traj.finished_at = data.get("finished_at")
        traj.termination_reason = data.get("termination_reason")
        traj.total_duration_seconds = data.get("total_duration_seconds", 0.0)
        traj.total_token_usage = data.get("total_token_usage", {})
        return traj


# ---------------------------------------------------------------------------
# Verification Result
# ---------------------------------------------------------------------------


class VerificationResult:
    """Result of independently verifying an agent's output.

    Attributes:
        run_id: The run being verified.
        passed: Whether the agent's output satisfies acceptance criteria.
        test_results: Individual test pass/fail results.
        existing_tests_passed: Whether pre-existing tests still pass.
        hidden_tests_passed: Whether hidden acceptance tests pass.
        regression_tests_passed: Whether regression checks pass.
        score: Normalized score in [0, 1].
        details: Human-readable verification details.
        verified_at: Timestamp of verification.
    """

    def __init__(
        self,
        run_id: str,
        passed: bool,
        verification_id: str | None = None,
        test_results: dict[str, bool] | None = None,
        existing_tests_passed: bool = True,
        hidden_tests_passed: bool = False,
        regression_tests_passed: bool = True,
        score: float = 0.0,
        details: str = "",
        # Extended fields for diagnosis
        public_tests_ran: bool = False,
        public_tests_passed: bool = False,
        public_tests_error: str | None = None,
        hidden_tests_ran: bool = False,
        hidden_tests_error: str | None = None,
        reference_solution_checked: bool = False,
        reference_solution_passed: bool = False,
        initial_defect_checked: bool = False,
        initial_defect_detected: bool = False,
    ):
        self.verification_id = verification_id or generate_id("verif-")
        self.run_id = run_id
        self.passed = passed
        self.test_results = test_results or {}
        self.existing_tests_passed = existing_tests_passed
        self.hidden_tests_passed = hidden_tests_passed
        self.regression_tests_passed = regression_tests_passed
        self.score = score
        self.details = details
        self.verified_at = datetime.utcnow().isoformat()
        # Extended fields
        self.public_tests_ran = public_tests_ran
        self.public_tests_passed = public_tests_passed
        self.public_tests_error = public_tests_error
        self.hidden_tests_ran = hidden_tests_ran
        self.hidden_tests_error = hidden_tests_error
        self.reference_solution_checked = reference_solution_checked
        self.reference_solution_passed = reference_solution_passed
        self.initial_defect_checked = initial_defect_checked
        self.initial_defect_detected = initial_defect_detected

    def to_dict(self) -> dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "run_id": self.run_id,
            "passed": self.passed,
            "test_results": self.test_results,
            "existing_tests_passed": self.existing_tests_passed,
            "hidden_tests_passed": self.hidden_tests_passed,
            "regression_tests_passed": self.regression_tests_passed,
            "score": self.score,
            "details": self.details,
            "verified_at": self.verified_at,
            "public_tests_ran": self.public_tests_ran,
            "public_tests_passed": self.public_tests_passed,
            "public_tests_error": self.public_tests_error,
            "hidden_tests_ran": self.hidden_tests_ran,
            "hidden_tests_error": self.hidden_tests_error,
            "reference_solution_checked": self.reference_solution_checked,
            "reference_solution_passed": self.reference_solution_passed,
            "initial_defect_checked": self.initial_defect_checked,
            "initial_defect_detected": self.initial_defect_detected,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationResult:
        return cls(
            verification_id=data.get("verification_id"),
            run_id=data["run_id"],
            passed=data["passed"],
            test_results=data.get("test_results", {}),
            existing_tests_passed=data.get("existing_tests_passed", True),
            hidden_tests_passed=data.get("hidden_tests_passed", False),
            regression_tests_passed=data.get("regression_tests_passed", True),
            score=data.get("score", 0.0),
            details=data.get("details", ""),
            public_tests_ran=data.get("public_tests_ran", False),
            public_tests_passed=data.get("public_tests_passed", False),
            public_tests_error=data.get("public_tests_error"),
            hidden_tests_ran=data.get("hidden_tests_ran", False),
            hidden_tests_error=data.get("hidden_tests_error"),
            reference_solution_checked=data.get("reference_solution_checked", False),
            reference_solution_passed=data.get("reference_solution_passed", False),
            initial_defect_checked=data.get("initial_defect_checked", False),
            initial_defect_detected=data.get("initial_defect_detected", False),
        )


# ---------------------------------------------------------------------------
# Failure Diagnosis
# ---------------------------------------------------------------------------


class FailureDiagnosis:
    """Diagnosis of why a run failed.

    Attributes:
        run_id: The run being diagnosed.
        primary_category: The main cause of failure.
        supporting_evidence: Evidence supporting this classification.
        contradictory_evidence: Evidence that contradicts this classification.
        confidence: Confidence score in [0, 1].
        affected_component: Which component is believed to be at fault.
        recommended_action: Suggested next step.
        diagnosis_version: Version of the diagnosis schema.
        diagnosed_at: Timestamp of diagnosis.
    """

    def __init__(
        self,
        run_id: str,
        primary_category: FailureCategory,
        diagnosis_id: str | None = None,
        supporting_evidence: list[str] | None = None,
        contradictory_evidence: list[str] | None = None,
        confidence: float = 0.5,
        affected_component: str | None = None,
        recommended_action: str = "",
    ):
        self.diagnosis_id = diagnosis_id or generate_id("diag-")
        self.run_id = run_id
        self.primary_category = primary_category
        self.supporting_evidence = supporting_evidence or []
        self.contradictory_evidence = contradictory_evidence or []
        self.confidence = confidence
        self.affected_component = affected_component
        self.recommended_action = recommended_action
        self.diagnosis_version = "1.0"
        self.diagnosed_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "run_id": self.run_id,
            "primary_category": (
                self.primary_category.value
                if isinstance(self.primary_category, FailureCategory)
                else self.primary_category
            ),
            "supporting_evidence": self.supporting_evidence,
            "contradictory_evidence": self.contradictory_evidence,
            "confidence": self.confidence,
            "affected_component": self.affected_component,
            "recommended_action": self.recommended_action,
            "diagnosis_version": self.diagnosis_version,
            "diagnosed_at": self.diagnosed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FailureDiagnosis:
        category = data.get("primary_category")
        if isinstance(category, str):
            try:
                category = FailureCategory(category)
            except ValueError:
                pass
        return cls(
            diagnosis_id=data.get("diagnosis_id"),
            run_id=data["run_id"],
            primary_category=category,
            supporting_evidence=data.get("supporting_evidence", []),
            contradictory_evidence=data.get("contradictory_evidence", []),
            confidence=data.get("confidence", 0.5),
            affected_component=data.get("affected_component"),
            recommended_action=data.get("recommended_action", ""),
        )


# ---------------------------------------------------------------------------
# Run Result
# ---------------------------------------------------------------------------


class RunResult:
    """Complete result of one agent run.

    Attributes:
        run_id: Unique identifier for this run.
        task_id: The task that was attempted.
        agent_id: The agent that executed.
        status: Final status of the run.
        trajectory: The complete execution trajectory.
        verification: Independent verification result.
        diagnosis: Failure diagnosis (if applicable).
        started_at: When the run started.
        finished_at: When the run finished.
        duration_seconds: Total wall-clock duration.
        agent_believes_success: Whether the agent claimed success.
        metadata: Additional data.
    """

    def __init__(
        self,
        run_id: str,
        task_id: str,
        agent_id: str,
        status: RunStatus = RunStatus.PENDING,
        result_id: str | None = None,
    ):
        self.result_id = result_id or generate_id("result-")
        self.run_id = run_id
        self.task_id = task_id
        self.agent_id = agent_id
        self.status = status
        self.trajectory: Trajectory | None = None
        self.verification: VerificationResult | None = None
        self.diagnosis: FailureDiagnosis | None = None
        self.started_at: str | None = None
        self.finished_at: str | None = None
        self.duration_seconds: float = 0.0
        self.agent_believes_success: bool = False
        self.metadata: dict[str, Any] = {}
        # Extended fields for diagnosis
        self.error: str | None = None
        self.step_count: int = 0
        self.agent_made_changes: bool = False
        self.passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": (self.status.value if isinstance(self.status, RunStatus) else self.status),
            "trajectory": self.trajectory.to_dict() if self.trajectory else None,
            "verification": self.verification.to_dict() if self.verification else None,
            "diagnosis": self.diagnosis.to_dict() if self.diagnosis else None,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "agent_believes_success": self.agent_believes_success,
            "metadata": self.metadata,
            "error": self.error,
            "step_count": self.step_count,
            "agent_made_changes": self.agent_made_changes,
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunResult:
        status = data.get("status")
        if isinstance(status, str):
            try:
                status = RunStatus(status)
            except ValueError:
                pass
        result = cls(
            result_id=data.get("result_id"),
            run_id=data["run_id"],
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            status=status,
        )
        if data.get("trajectory"):
            result.trajectory = Trajectory.from_dict(data["trajectory"])
        if data.get("verification"):
            result.verification = VerificationResult.from_dict(data["verification"])
        if data.get("diagnosis"):
            result.diagnosis = FailureDiagnosis.from_dict(data["diagnosis"])
        result.started_at = data.get("started_at")
        result.finished_at = data.get("finished_at")
        result.duration_seconds = data.get("duration_seconds", 0.0)
        result.agent_believes_success = data.get("agent_believes_success", False)
        result.metadata = data.get("metadata", {})
        result.error = data.get("error")
        result.step_count = data.get("step_count", 0)
        result.agent_made_changes = data.get("agent_made_changes", False)
        result.passed = data.get("passed", False)
        return result


# ---------------------------------------------------------------------------
# Curriculum State
# ---------------------------------------------------------------------------


class CurriculumState:
    """Snapshot of the adaptive curriculum's current state.

    Attributes:
        curriculum_id: Unique identifier.
        strategy: Current selection strategy.
        capability_scores: Per-capability performance estimates.
        task_pool: List of available task IDs.
        selected_tasks: Tasks selected for the next cycle.
        generation: Current curriculum generation number.
        updated_at: Last update timestamp.
    """

    def __init__(
        self,
        strategy: CurriculumStrategy = CurriculumStrategy.STATIC,
        curriculum_id: str | None = None,
        capability_scores: dict[str, float] | None = None,
        task_pool: list[str] | None = None,
        selected_tasks: list[str] | None = None,
        generation: int = 0,
    ):
        self.curriculum_id = curriculum_id or generate_id("curr-")
        self.strategy = strategy
        self.capability_scores = capability_scores or {}
        self.task_pool = task_pool or []
        self.selected_tasks = selected_tasks or []
        self.generation = generation
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "curriculum_id": self.curriculum_id,
            "strategy": (self.strategy.value if isinstance(self.strategy, CurriculumStrategy) else self.strategy),
            "capability_scores": self.capability_scores,
            "task_pool": self.task_pool,
            "selected_tasks": self.selected_tasks,
            "generation": self.generation,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CurriculumState:
        strategy = data.get("strategy")
        if isinstance(strategy, str):
            try:
                strategy = CurriculumStrategy(strategy)
            except ValueError:
                pass
        return cls(
            curriculum_id=data.get("curriculum_id"),
            strategy=strategy,
            capability_scores=data.get("capability_scores", {}),
            task_pool=data.get("task_pool", []),
            selected_tasks=data.get("selected_tasks", []),
            generation=data.get("generation", 0),
        )


# ---------------------------------------------------------------------------
# Experiment Configuration
# ---------------------------------------------------------------------------


class ExperimentConfig:
    """Configuration for a research experiment.

    Attributes:
        experiment_id: Unique identifier.
        name: Human-readable name.
        description: Detailed description.
        hypothesis: Research hypothesis being tested.
        agent_config: Agent configuration for this experiment.
        task_selection_strategy: How tasks are selected.
        inference_budget: Budget constraint (e.g. max API calls).
        model_identifier: Model used in this experiment.
        random_seed: Seed for reproducibility.
        evaluation_set_id: ID of the held-out evaluation set.
        metadata: Additional configuration.
    """

    def __init__(
        self,
        name: str,
        experiment_id: str | None = None,
        description: str = "",
        hypothesis: str = "",
        agent_config: dict[str, Any] | None = None,
        task_selection_strategy: CurriculumStrategy = CurriculumStrategy.STATIC,
        inference_budget: int | None = None,
        model_identifier: str | None = None,
        random_seed: int | None = None,
        evaluation_set_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.experiment_id = experiment_id or generate_id("exp-")
        self.name = name
        self.description = description
        self.hypothesis = hypothesis
        self.agent_config = agent_config or {}
        self.task_selection_strategy = task_selection_strategy
        self.inference_budget = inference_budget
        self.model_identifier = model_identifier
        self.random_seed = random_seed
        self.evaluation_set_id = evaluation_set_id
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()
        self.started_at: str | None = None
        self.finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "hypothesis": self.hypothesis,
            "agent_config": self.agent_config,
            "task_selection_strategy": (
                self.task_selection_strategy.value
                if isinstance(self.task_selection_strategy, CurriculumStrategy)
                else self.task_selection_strategy
            ),
            "inference_budget": self.inference_budget,
            "model_identifier": self.model_identifier,
            "random_seed": self.random_seed,
            "evaluation_set_id": self.evaluation_set_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentConfig:
        strategy = data.get("task_selection_strategy")
        if isinstance(strategy, str):
            try:
                strategy = CurriculumStrategy(strategy)
            except ValueError:
                pass
        return cls(
            experiment_id=data.get("experiment_id"),
            name=data["name"],
            description=data.get("description", ""),
            hypothesis=data.get("hypothesis", ""),
            agent_config=data.get("agent_config", {}),
            task_selection_strategy=strategy,
            inference_budget=data.get("inference_budget"),
            model_identifier=data.get("model_identifier"),
            random_seed=data.get("random_seed"),
            evaluation_set_id=data.get("evaluation_set_id"),
            metadata=data.get("metadata", {}),
        )
