"""ScriptAgent: executes external Python scripts as agents.

Runs a user-provided Python script with access to the workspace and task
information. The script receives task details via environment variables
and a config file, and modifies the workspace directly.

Enables research experiments with custom agent logic without modifying
the core codebase.
"""

from __future__ import annotations

import json
import subprocess
import sys
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


class ScriptAgent(BaseAgent):
    """Agent that executes an external Python script.

    The script receives:
    - Task info via environment variables (FORGELAB_TASK_ID, etc.)
    - A JSON config file at the workspace root
    - Direct access to the workspace directory

    The script should modify files in the workspace to fix the bug.

    Args:
        config: Agent configuration.
        script_path: Path to the Python script to execute.
        timeout: Maximum execution time in seconds (default: 300).
        python_executable: Python interpreter to use (default: sys.executable).
        extra_env: Additional environment variables to pass.
    """

    def __init__(
        self,
        config: AgentConfig,
        script_path: str,
        timeout: int = 300,
        python_executable: str = None,
        extra_env: dict[str, str] = None,
    ):
        super().__init__(config)
        self.script_path = script_path
        self.timeout = timeout
        self.python_executable = python_executable or sys.executable
        self.extra_env = extra_env or {}
        self._stdout: str = ""
        self._stderr: str = ""
        self._exit_code: int = -1

    def execute(
        self,
        task: TaskSpec,
        workspace: Path,
        run_config: RunConfig,
    ) -> Trajectory:
        """Execute the external script.

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

        # Step 1: Prepare config file
        config_file = workspace / ".forgelab_task_config.json"
        config_data = {
            "task_id": task.task_id,
            "description": task.description,
            "world_id": getattr(task, "world_id", ""),
            "mutation_id": getattr(task, "mutation_id", ""),
            "category": str(task.category) if hasattr(task, "category") else "",
            "difficulty_level": task.difficulty_level,
            "constraints": task.constraints,
            "workspace": str(workspace),
        }
        config_file.write_text(json.dumps(config_data, indent=2, default=str))

        step = TrajectoryStep(
            step_index=step_index,
            observation="Preparing config file",
            action="prepare_config",
            tool_name="prepare_config",
            tool_arguments={"config_file": str(config_file)},
            tool_result=f"Written {config_file.stat().st_size} bytes",
            duration_seconds=0.01,
        )
        trajectory.add_step(step)
        step_index += 1

        # Step 2: List workspace files
        step = self._list_files_step(workspace, step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 3: Execute the script
        step = self._execute_script_step(workspace, task, step_index)
        trajectory.add_step(step)
        step_index += 1

        # Step 4: Report result
        duration = time.time() - start_time
        step = TrajectoryStep(
            step_index=step_index,
            observation="Reporting result",
            action="report",
            tool_name="report",
            tool_arguments={},
            tool_result=f"Exit code: {self._exit_code}, duration: {duration:.2f}s",
            duration_seconds=0.01,
            metadata={
                "exit_code": self._exit_code,
                "success": self._exit_code == 0,
            },
        )
        trajectory.add_step(step)

        trajectory.finalize(
            termination_reason="completed",
            total_duration_seconds=duration,
        )

        return trajectory

    def _list_files_step(self, workspace: Path, step_index: int) -> TrajectoryStep:
        """List files in the workspace."""
        files = []
        if workspace.exists():
            for f in workspace.rglob("*"):
                if f.is_file() and not str(f).endswith(".pyc"):
                    files.append(str(f.relative_to(workspace)))

        return TrajectoryStep(
            step_index=step_index,
            observation="Listing files in workspace",
            action="list_files",
            tool_name="list_files",
            tool_arguments={"path": str(workspace)},
            tool_result=str(files),
            duration_seconds=0.01,
        )

    def _execute_script_step(self, workspace: Path, task: TaskSpec, step_index: int) -> TrajectoryStep:
        """Execute the external script.

        Args:
            workspace: Path to the workspace.
            task: The task specification.
            step_index: Current step index.

        Returns:
            TrajectoryStep describing the execution result.
        """
        script = Path(self.script_path)
        if not script.exists():
            return TrajectoryStep(
                step_index=step_index,
                observation="Executing script",
                action="run_script",
                tool_name="run_script",
                tool_arguments={"script": str(script)},
                tool_result=f"Script not found: {self.script_path}",
                duration_seconds=0.0,
                error="script_not_found",
                metadata={"exit_code": -1},
            )

        # Build environment
        env = {
            "FORGELAB_TASK_ID": task.task_id,
            "FORGELAB_WORKSPACE": str(workspace),
            "FORGELAB_TASK_DESCRIPTION": task.description,
            "FORGELAB_DIFFICULTY": str(task.difficulty_level),
        }
        env.update(self.extra_env)

        start = time.time()
        try:
            result = subprocess.run(
                [self.python_executable, str(script)],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**dict(__import__("os").environ), **env},
            )
            self._exit_code = result.returncode
            self._stdout = result.stdout
            self._stderr = result.stderr

        except subprocess.TimeoutExpired:
            self._exit_code = -1
            self._stdout = ""
            self._stderr = f"Script timed out after {self.timeout} seconds"
        except Exception as e:
            self._exit_code = -1
            self._stdout = ""
            self._stderr = str(e)

        duration = time.time() - start

        return TrajectoryStep(
            step_index=step_index,
            observation="Executing script",
            action="run_script",
            tool_name="run_script",
            tool_arguments={
                "script": str(script),
                "timeout": self.timeout,
                "cwd": str(workspace),
            },
            tool_result=f"Exit code: {self._exit_code}, stdout: {self._stdout[:1000]}",
            duration_seconds=duration,
            metadata={
                "exit_code": self._exit_code,
                "success": self._exit_code == 0,
            },
        )

    def get_available_tools(self) -> list[str]:
        """List available tool names.

        Returns:
            List of tool name strings.
        """
        return ["list_files", "run_script", "report"]

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics.

        Returns:
            Dictionary of stats including script info.
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "script_path": self.script_path,
            "timeout": self.timeout,
            "last_exit_code": self._exit_code,
        }
