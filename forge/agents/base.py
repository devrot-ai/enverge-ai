"""Base agent interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from forge.core.schemas import (
    AgentConfig,
    RunConfig,
    TaskSpec,
    Trajectory,
)


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Agents execute tasks in workspaces using tools.
    Subclasses implement the actual execution logic.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.agent_id = config.agent_id
        self.agent_type = config.agent_type

    @abstractmethod
    def execute(
        self,
        task: TaskSpec,
        workspace: Path,
        run_config: RunConfig,
    ) -> Trajectory:
        """Execute an agent run.

        Args:
            task: The task specification.
            workspace: Path to the agent's workspace.
            run_config: Run configuration.

        Returns:
            Complete execution trajectory.
        """
        raise NotImplementedError

    @abstractmethod
    def get_available_tools(self) -> list[str]:
        """List available tool names.

        Returns:
            List of tool name strings.
        """
        raise NotImplementedError

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics.

        Returns:
            Dictionary of stats.
        """
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
        }
