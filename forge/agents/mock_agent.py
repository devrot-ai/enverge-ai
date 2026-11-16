"""MockAgent: deterministic agent for testing infrastructure.

Simulates agent behavior without requiring an API key.
Supports configurable scenarios: success, partial, failure, no_change.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from forge.agents.base import BaseAgent
from forge.core.schemas import (
    AgentConfig,
    RunConfig,
    TaskSpec,
    Trajectory,
    TrajectoryStep,
)
from forge.world_factory.seeder import revert_mutation


class MockAgent(BaseAgent):
    """Deterministic mock agent for testing.

    Behaves according to a predefined scenario:
    - "success": Applies the reference fix correctly
    - "partial": Makes partial changes but doesn't fully fix
    - "failure": Makes incorrect changes
    - "no_change": Makes no changes to the codebase

    All runs are clearly labeled as simulations.
    """

    def __init__(self, config: AgentConfig, scenario: str = "success"):
        self.metadata: dict[str, Any] = {}
        super().__init__(config)
        self.scenario = scenario
        self.metadata["scenario"] = scenario
        self.metadata["is_simulation"] = True

    def execute(
        self,
        task: TaskSpec,
        workspace: Path,
        run_config: RunConfig,
    ) -> Trajectory:
        """Execute a mock agent run.

        Args:
            task: The task specification.
            workspace: Path to the agent's workspace.
            run_config: Run configuration.

        Returns:
            Complete execution trajectory.
        """
        trajectory = Trajectory(
            run_id=run_config.run_id,
            task_id=task.task_id,
            agent_id=self.agent_id,
        )

        start_time = time.time()
        step_index = 0

        # Step 1: List files
        step = self._list_files_step(workspace, step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 2: Read the main file
        step = self._read_file_step(workspace, "app.py", step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 3: Read public tests
        step = self._read_file_step(workspace, "tests/test_public.py", step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 4: Search for the bug
        step = self._search_code_step(workspace, step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 5: Apply fix based on scenario
        step = self._apply_fix_step(workspace, task, step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 6: Run tests
        step = self._run_tests_step(workspace, step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 7: Finish
        step = self._finish_step(step_index)
        trajectory.add_step(step)

        duration = time.time() - start_time
        trajectory.finalize(
            termination_reason="completed",
            total_duration_seconds=duration,
        )

        return trajectory

    def _list_files_step(self, workspace: Path, step_index: int) -> TrajectoryStep:
        """Simulate listing files."""
        files = []
        for item in workspace.rglob("*"):
            if item.is_file() and not str(item).startswith(str(workspace / ".hidden")):
                files.append(str(item.relative_to(workspace)))

        return TrajectoryStep(
            step_index=step_index,
            observation="Listing workspace files",
            action="list_files",
            tool_name="list_files",
            tool_arguments={"path": "."},
            tool_result="\n".join(files[:20]),
        )

    def _read_file_step(self, workspace: Path, filename: str, step_index: int) -> TrajectoryStep:
        """Simulate reading a file."""
        filepath = workspace / filename
        if filepath.exists():
            content = filepath.read_text()
            return TrajectoryStep(
                step_index=step_index,
                observation=f"Reading {filename}",
                action="read_file",
                tool_name="read_file",
                tool_arguments={"path": filename},
                tool_result=content[:500] + ("..." if len(content) > 500 else ""),
            )
        return TrajectoryStep(
            step_index=step_index,
            observation=f"Reading {filename}",
            action="read_file",
            tool_name="read_file",
            tool_arguments={"path": filename},
            tool_result=f"File not found: {filename}",
            error=f"File not found: {filename}",
        )

    def _search_code_step(self, workspace: Path, step_index: int) -> TrajectoryStep:
        """Simulate searching for code."""
        return TrajectoryStep(
            step_index=step_index,
            observation="Searching for bug-related code",
            action="search_code",
            tool_name="search_code",
            tool_arguments={"pattern": "BUG|bug|fix|todo"},
            tool_result="Found potential bug in app.py: list_tasks method",
        )

    def _apply_fix_step(self, workspace: Path, task: TaskSpec, step_index: int) -> TrajectoryStep:
        """Simulate applying a fix based on scenario."""
        mutation_id = task.metadata.get("mutation_id", "")

        if self.scenario == "success" and mutation_id:
            # Apply the reference fix
            try:
                revert_mutation(workspace, mutation_id)
                return TrajectoryStep(
                    step_index=step_index,
                    observation="Applying fix to app.py",
                    action="write_file",
                    tool_name="write_file",
                    tool_arguments={"path": "app.py"},
                    tool_result="Fix applied successfully",
                )
            except Exception as e:
                return TrajectoryStep(
                    step_index=step_index,
                    observation="Applying fix to app.py",
                    action="write_file",
                    tool_name="write_file",
                    tool_arguments={"path": "app.py"},
                    tool_result=f"Error applying fix: {e}",
                    error=str(e),
                )
        elif self.scenario == "partial":
            return TrajectoryStep(
                step_index=step_index,
                observation="Making partial changes",
                action="write_file",
                tool_name="write_file",
                tool_arguments={"path": "app.py"},
                tool_result="Partial fix applied - may not fully resolve the issue",
            )
        elif self.scenario == "failure":
            return TrajectoryStep(
                step_index=step_index,
                observation="Making incorrect changes",
                action="write_file",
                tool_name="write_file",
                tool_arguments={"path": "app.py"},
                tool_result="Incorrect fix applied",
            )
        else:  # no_change
            return TrajectoryStep(
                step_index=step_index,
                observation="No changes made",
                action="no_op",
                tool_name="no_op",
                tool_arguments={},
                tool_result="Agent decided not to make changes",
            )

    def _run_tests_step(self, workspace: Path, step_index: int) -> TrajectoryStep:
        """Simulate running tests."""
        return TrajectoryStep(
            step_index=step_index,
            observation="Running public tests",
            action="run_public_tests",
            tool_name="run_public_tests",
            tool_arguments={"path": "tests/test_public.py"},
            tool_result="Tests executed (mock output)",
        )

    def _finish_step(self, step_index: int) -> TrajectoryStep:
        """Simulate finishing the task."""
        believes_success = self.scenario in ("success", "partial")
        return TrajectoryStep(
            step_index=step_index,
            observation="Task complete",
            action="finish_task",
            tool_name="finish_task",
            tool_arguments={"success": believes_success},
            tool_result=f"Agent believes task is {'solved' if believes_success else 'not solved'}",
        )

    def get_available_tools(self) -> list[str]:
        """List available tool names."""
        return [
            "list_files",
            "read_file",
            "search_code",
            "write_file",
            "run_public_tests",
            "inspect_test_output",
            "inspect_git_diff",
            "finish_task",
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "scenario": self.scenario,
            "is_simulation": True,
        }
