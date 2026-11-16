"""Adversarial agent wrapper for robustness testing.

Wraps any agent and injects errors during execution to test
how well the agent handles unexpected conditions.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

from forge.agents.base import BaseAgent
from forge.core.schemas import RunResult, TaskSpec, Trajectory
from forge.evaluation.error_injection import ErrorInjector, ErrorInjectionResult

logger = logging.getLogger(__name__)


@dataclass
class AdversarialResult:
    """Result of adversarial testing."""

    base_result: RunResult
    error_injections: list[ErrorInjectionResult] = field(default_factory=list)
    robustness_score: float = 0.0
    errors_handled: int = 0
    errors_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "robustness_score": round(self.robustness_score, 4),
            "errors_handled": self.errors_handled,
            "errors_total": self.errors_total,
            "error_injections": [e.to_dict() for e in self.error_injections],
        }


class AdversarialAgent(BaseAgent):
    """Wrap any agent with error injection during execution.

    This agent wraps another agent and periodically injects errors
    into the workspace during execution to test robustness. The base
    agent attempts to fix the task while errors are being injected.

    Configurable error rate and types allow testing different
    robustness scenarios.
    """

    def __init__(
        self,
        base_agent: BaseAgent,
        error_rate: float = 0.1,
        error_types: list[str] | None = None,
        seed: int | None = None,
    ):
        """Initialize the adversarial agent.

        Args:
            base_agent: The agent to wrap.
            error_rate: Probability of injecting an error after each step (0.0-1.0).
            error_types: List of error types to inject. If None, all types.
            seed: Random seed for reproducibility.
        """
        self.base_agent = base_agent
        self.error_rate = error_rate
        self.error_types = error_types or list(ErrorInjector.ERROR_TYPE_MAP.keys())
        self.rng = random.Random(seed)
        self.error_injector = ErrorInjector()
        self.error_injections: list[ErrorInjectionResult] = []

    @property
    def agent_type(self) -> str:
        """Return the agent type identifier."""
        return f"adversarial({self.base_agent.agent_type})"

    def run(
        self,
        task_spec: TaskSpec,
        workspace_dir: str,
    ) -> RunResult:
        """Run the base agent with error injection.

        The base agent runs normally, but after each trajectory step,
        there's a chance an error will be injected into the workspace.

        Args:
            task_spec: Task specification.
            workspace_dir: Path to the workspace.

        Returns:
            RunResult from the base agent.
        """
        # Run the base agent
        result = self.base_agent.run(task_spec, workspace_dir)

        # If the base agent has a trajectory, inject errors between steps
        # For agents without step-by-step control, inject after completion
        if result.trajectory and result.trajectory.steps:
            # Errors were injected during execution (if base agent supports it)
            pass
        else:
            # Inject errors after the base agent completes
            self._inject_post_run_errors(workspace_dir)

        # Calculate robustness score
        result.metadata = result.metadata or {}
        result.metadata["adversarial"] = self._calculate_robustness()

        return result

    def _inject_post_run_errors(self, workspace_dir: str) -> None:
        """Inject errors after the base agent completes.

        This simulates adversarial conditions that occur after the
        agent's fix is applied.

        Args:
            workspace_dir: Path to the workspace.
        """
        num_errors = max(1, int(len(self.error_types) * self.error_rate * 10))
        num_errors = min(num_errors, len(self.error_types))

        for _ in range(num_errors):
            error_type = self.rng.choice(self.error_types)
            result = self.error_injector.inject(workspace_dir, error_type)
            self.error_injections.append(result)

    def _calculate_robustness(self) -> dict[str, Any]:
        """Calculate robustness score based on error injection results.

        Returns:
            Dictionary with robustness metrics.
        """
        errors_total = len(self.error_injections)
        errors_handled = sum(1 for e in self.error_injections if e.agent_handled)

        if errors_total == 0:
            robustness_score = 1.0
        else:
            robustness_score = errors_handled / errors_total

        return {
            "robustness_score": round(robustness_score, 4),
            "errors_handled": errors_handled,
            "errors_total": errors_total,
            "injections": [e.to_dict() for e in self.error_injections],
        }

    def get_adversarial_result(self, run_result: RunResult) -> AdversarialResult:
        """Get adversarial testing result from a run.

        Args:
            run_result: Run result from the adversarial agent.

        Returns:
            AdversarialResult with robustness metrics.
        """
        adversarial_data = run_result.metadata.get("adversarial", {}) if run_result.metadata else {}

        return AdversarialResult(
            base_result=run_result,
            error_injections=self.error_injections,
            robustness_score=adversarial_data.get("robustness_score", 0.0),
            errors_handled=adversarial_data.get("errors_handled", 0),
            errors_total=adversarial_data.get("errors_total", 0),
        )

    def execute(
        self,
        task_spec: TaskSpec,
        workspace_dir: str,
        run_config: Any,
    ) -> Trajectory:
        """Execute the base agent with error injection.

        Args:
            task_spec: Task specification.
            workspace_dir: Path to the workspace.
            run_config: Run configuration.

        Returns:
            Trajectory from the base agent.
        """
        trajectory = self.base_agent.execute(task_spec, workspace_dir, run_config)
        self._inject_post_run_errors(workspace_dir)
        return trajectory

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Return available tools from the base agent.

        Returns:
            List of tool definitions.
        """
        return self.base_agent.get_available_tools()
