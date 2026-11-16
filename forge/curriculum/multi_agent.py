"""Multi-agent curriculum tracking.

Enables curriculum that tracks multiple agents simultaneously with
per-agent capability tracking and optional cross-agent knowledge transfer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from forge.core.schemas import TaskCategory, TaskSpec
from forge.curriculum.capability_tracker import CapabilityTracker
from forge.curriculum.selector import CurriculumSelector

logger = logging.getLogger(__name__)


@dataclass
class AgentCurriculumState:
    """Curriculum state for a single agent."""

    agent_type: str
    capability_tracker: CapabilityTracker = field(default_factory=CapabilityTracker)
    tasks_completed: int = 0
    tasks_passed: int = 0
    last_task_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_type": self.agent_type,
            "tasks_completed": self.tasks_completed,
            "tasks_passed": self.tasks_passed,
            "last_task_id": self.last_task_id,
            "pass_rate": self.tasks_passed / self.tasks_completed if self.tasks_completed > 0 else 0.0,
        }


class SharingLevel:
    """Configurable sharing levels for cross-agent knowledge transfer."""

    NONE = "none"
    PARTIAL = "partial"  # Share within same template
    FULL = "full"  # Share all tasks


class MultiAgentCurriculum:
    """Curriculum that tracks multiple agents simultaneously.

    Each agent maintains its own capability tracking while drawing from
    a shared task pool. Optional cross-agent knowledge transfer allows
    agents to benefit from each other's progress.

    Sharing levels:
    - none: Each agent tracks independently, no sharing
    - partial: If Agent A passes a task, Agent B may get similar tasks (same template)
    - full: All agents share all task results
    """

    def __init__(self, sharing_level: str = SharingLevel.NONE):
        """Initialize the multi-agent curriculum.

        Args:
            sharing_level: Level of cross-agent knowledge transfer.
        """
        self.agents: dict[str, AgentCurriculumState] = {}
        self.sharing_level = sharing_level
        self.all_tasks: list[TaskSpec] = []
        self.completed_tasks: set[str] = set()

    def add_agent(self, agent_type: str) -> None:
        """Register a new agent for curriculum tracking.

        Args:
            agent_type: Identifier for the agent (e.g., 'mock', 'rule_based').
        """
        if agent_type not in self.agents:
            self.agents[agent_type] = AgentCurriculumState(agent_type=agent_type)
            logger.info("Added agent %s to multi-agent curriculum", agent_type)

    def set_task_pool(self, tasks: list[TaskSpec]) -> None:
        """Set the shared task pool for all agents.

        Args:
            tasks: List of available tasks.
        """
        self.all_tasks = tasks

    def select_task(self, agent_type: str) -> TaskSpec | None:
        """Select the next task for an agent.

        Args:
            agent_type: The agent requesting a task.

        Returns:
            Next TaskSpec or None if no tasks available.
        """
        if agent_type not in self.agents:
            self.add_agent(agent_type)

        state = self.agents[agent_type]
        tracker = state.capability_tracker

        # Get available tasks (not completed by this agent)
        available = [t for t in self.all_tasks if t.task_id not in self.completed_tasks]

        if not available:
            return None

        # Use capability tracker to select task
        if state.capability_tracker.capabilities:
            weaknesses = state.capability_tracker.get_weaknesses()
            if weaknesses:
                weakest_cap = weaknesses[0]
                # Prefer tasks that test weak capabilities
                for task in available:
                    if task.capabilities and weakest_cap in task.capabilities:
                        return task

        # Fallback: random selection
        import random

        return random.choice(available)

    def update(self, agent_type: str, task_id: str, passed: bool, result: dict[str, Any] | None = None) -> None:
        """Update curriculum state after an agent completes a task.

        Args:
            agent_type: The agent that completed the task.
            task_id: The task that was completed.
            passed: Whether the agent passed the task.
            result: Optional result details.
        """
        if agent_type not in self.agents:
            self.add_agent(agent_type)

        state = self.agents[agent_type]
        state.tasks_completed += 1
        if passed:
            state.tasks_passed += 1
        state.last_task_id = task_id

        # Update capability tracker
        if result and "capabilities" in result:
            for capability in result["capabilities"]:
                state.capability_tracker.update(capability, passed)

        # Cross-agent knowledge transfer
        if self.sharing_level != SharingLevel.NONE:
            self._share_knowledge(agent_type, task_id, passed, result)

    def _share_knowledge(self, source_agent: str, task_id: str, passed: bool, result: dict[str, Any] | None) -> None:
        """Share knowledge from one agent to others based on sharing level.

        Args:
            source_agent: The agent that completed the task.
            task_id: The task that was completed.
            passed: Whether the source agent passed.
            result: Optional result details.
        """
        if self.sharing_level == SharingLevel.FULL:
            # Share with all other agents
            for agent_type, state in self.agents.items():
                if agent_type != source_agent:
                    if result and "capabilities" in result:
                        for capability in result["capabilities"]:
                            state.capability_tracker.update(capability, passed)

        elif self.sharing_level == SharingLevel.PARTIAL:
            # Only share within same template (simplified: share pass rate)
            source_state = self.agents[source_agent]
            source_task = next((t for t in self.all_tasks if t.task_id == task_id), None)

            if source_task:
                for agent_type, state in self.agents.items():
                    if agent_type != source_agent:
                        # Share template-level knowledge
                        if source_task.category:
                            state.capability_tracker.update(source_task.category.value, passed)

    def get_agent_state(self, agent_type: str) -> AgentCurriculumState | None:
        """Get the curriculum state for an agent.

        Args:
            agent_type: The agent to query.

        Returns:
            AgentCurriculumState or None if agent not found.
        """
        return self.agents.get(agent_type)

    def get_all_states(self) -> dict[str, AgentCurriculumState]:
        """Get curriculum states for all agents.

        Returns:
            Dict of agent_type -> AgentCurriculumState.
        """
        return dict(self.agents)

    def get_comparison(self) -> dict[str, dict[str, Any]]:
        """Get comparison of all agent states.

        Returns:
            Dict of agent_type -> state dict for comparison.
        """
        return {agent_type: state.to_dict() for agent_type, state in self.agents.items()}

    def to_dict(self) -> dict[str, Any]:
        """Serialize entire curriculum state.

        Returns:
            Dict with all agent states and configuration.
        """
        return {
            "sharing_level": self.sharing_level,
            "agents": {agent_type: state.to_dict() for agent_type, state in self.agents.items()},
            "task_pool_size": len(self.all_tasks),
            "completed_tasks": len(self.completed_tasks),
        }
