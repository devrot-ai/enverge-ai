"""Run orchestrator: executes the complete agent run lifecycle.

Manages workspace setup, agent execution, verification, and cleanup.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from forge.agents.base import BaseAgent
from forge.core.schemas import (
    FailureCategory,
    FailureDiagnosis,
    RunConfig,
    RunResult,
    RunStatus,
    TaskSpec,
    VerificationResult,
    WorldSpec,
)
from forge.evaluation.verifier import Verifier
from forge.validators.world_validator import WorldValidator

logger = logging.getLogger(__name__)


class RunOrchestrator:
    """Orchestrates the complete agent run lifecycle.

    Lifecycle:
    1. Create run identifier
    2. Load validated task
    3. Create fresh agent workspace
    4. Initialize agent
    5. Execute agent interaction loop
    6. Record trajectory
    7. Freeze agent workspace
    8. Send to independent verifier
    9. Create final RunResult
    10. Store artifacts
    11. Clean up
    """

    def __init__(
        self,
        artifacts_dir: str | None = None,
    ):
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else Path("runs")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.verifier = Verifier()
        self.world_validator = WorldValidator()

    def run(
        self,
        task: TaskSpec,
        world: WorldSpec,
        agent: BaseAgent,
        run_config: RunConfig,
    ) -> RunResult:
        """Execute a complete agent run.

        Args:
            task: The task specification.
            world: The world specification.
            agent: The agent to execute.
            run_config: Run configuration.

        Returns:
            Complete RunResult with trajectory, verification, and diagnosis.
        """
        result = RunResult(
            run_id=run_config.run_id,
            task_id=task.task_id,
            agent_id=agent.agent_id,
            status=RunStatus.RUNNING,
        )
        result.started_at = datetime.utcnow().isoformat()

        world_dir = Path(world.metadata.get("world_dir", ""))
        workspace_dir = self._create_workspace(world_dir, run_config.run_id)

        try:
            # Execute agent
            logger.info(f"Running agent {agent.agent_id} on task {task.task_id}")
            trajectory = agent.execute(task, workspace_dir, run_config)
            result.trajectory = trajectory

            # Check if agent believes it succeeded
            for step in trajectory.steps:
                if step.tool_name == "finish_task":
                    result.agent_believes_success = step.tool_arguments.get("success", False)
                    break

            # Verify independently
            verification = self.verifier.verify(workspace_dir, world)
            result.verification = verification

            # Determine status
            result.passed = verification.passed
            if verification.passed:
                result.status = RunStatus.COMPLETED
            else:
                result.status = RunStatus.FAILED

            # Diagnose if failed
            if not verification.passed:
                diagnosis = self._diagnose(result, task, world, verification)
                result.diagnosis = diagnosis

        except Exception as e:
            logger.error(f"Run {run_config.run_id} failed: {e}")
            result.status = RunStatus.FAILED
            result.diagnosis = FailureDiagnosis(
                run_id=run_config.run_id,
                primary_category=FailureCategory.INFRASTRUCTURE_FAILURE,
                supporting_evidence=[str(e)],
                confidence=0.9,
                recommended_action="Check infrastructure and retry",
            )
        finally:
            result.finished_at = datetime.utcnow().isoformat()
            result.duration_seconds = self._compute_duration(result.started_at, result.finished_at)

            # Store artifacts
            self._store_artifacts(result)

            # Cleanup workspace
            self._cleanup_workspace(workspace_dir)

        return result

    def _create_workspace(self, world_dir: Path, run_id: str) -> Path:
        """Create a fresh workspace by copying the world directory.

        Args:
            world_dir: Source world directory.
            run_id: Run identifier for naming.

        Returns:
            Path to the new workspace.
        """
        workspace_dir = self.artifacts_dir / f"workspace_{run_id}"
        shutil.copytree(world_dir, workspace_dir, symlinks=True)
        return workspace_dir

    def _diagnose(
        self,
        result: RunResult,
        task: TaskSpec,
        world: WorldSpec,
        verification: VerificationResult,
    ) -> FailureDiagnosis:
        """Diagnose why a run failed.

        Args:
            result: The run result.
            task: The task specification.
            world: The world specification.
            verification: The verification result.

        Returns:
            Failure diagnosis.
        """
        evidence = []
        contradictory = []

        # Check if verification itself might be broken
        if not verification.existing_tests_passed:
            evidence.append("Existing tests failed - possible environment issue")

        if not verification.hidden_tests_passed:
            evidence.append("Hidden tests failed - agent did not fix the bug")

        # Check trajectory for errors
        if result.trajectory:
            error_steps = [s for s in result.trajectory.steps if s.error]
            if error_steps:
                evidence.append(f"Agent encountered {len(error_steps)} errors during execution")

        # Determine category
        if not verification.existing_tests_passed:
            category = FailureCategory.ENVIRONMENT_FAILURE
            confidence = 0.7
        elif not result.agent_believes_success and not verification.hidden_tests_passed:
            category = FailureCategory.AGENT_FAILURE
            confidence = 0.9
        else:
            category = FailureCategory.AGENT_FAILURE
            confidence = 0.8

        return FailureDiagnosis(
            run_id=result.run_id,
            primary_category=category,
            supporting_evidence=evidence,
            contradictory_evidence=contradictory,
            confidence=confidence,
            affected_component="agent" if category == FailureCategory.AGENT_FAILURE else "environment",
            recommended_action=self._get_recommendation(category),
        )

    def _get_recommendation(self, category: FailureCategory) -> str:
        """Get a recommendation based on failure category."""
        recommendations = {
            FailureCategory.AGENT_FAILURE: "Generate targeted tasks for agent's weak capabilities",
            FailureCategory.ENVIRONMENT_FAILURE: "Repair the world template and revalidate",
            FailureCategory.INVALID_TASK: "Revise the task specification",
            FailureCategory.VERIFIER_FAILURE: "Repair the hidden tests",
            FailureCategory.INFRASTRUCTURE_FAILURE: "Check system resources and retry",
            FailureCategory.UNCERTAIN: "Collect more data before deciding",
        }
        return recommendations.get(category, "Investigate further")

    def _compute_duration(self, started_at: str | None, finished_at: str | None) -> float:
        """Compute duration in seconds between two ISO timestamps."""
        if not started_at or not finished_at:
            return 0.0
        try:
            start = datetime.fromisoformat(started_at)
            end = datetime.fromisoformat(finished_at)
            return (end - start).total_seconds()
        except (ValueError, TypeError):
            return 0.0

    def _store_artifacts(self, result: RunResult) -> None:
        """Store run artifacts to disk.

        Args:
            result: The run result to store.
        """
        run_dir = self.artifacts_dir / result.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Store result as JSON
        result_path = run_dir / "result.json"
        result_path.write_text(json.dumps(result.to_dict(), indent=2, default=str))

        # Store trajectory as JSONL
        if result.trajectory:
            traj_path = run_dir / "trajectory.jsonl"
            with open(traj_path, "w") as f:
                for step in result.trajectory.steps:
                    f.write(json.dumps(step.to_dict(), default=str) + "\n")

    def _cleanup_workspace(self, workspace_dir: Path) -> None:
        """Clean up the workspace directory.

        Args:
            workspace_dir: Path to the workspace.
        """
        if workspace_dir.exists():
            try:
                shutil.rmtree(workspace_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup workspace {workspace_dir}: {e}")
