"""Agent registry for managing registered agent types.

Provides a central registry for agent factory functions so new agent
types can be added without modifying existing code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from forge.agents.base import BaseAgent
from forge.core.schemas import AgentConfig


class AgentRegistry:
    """Central registry for agent types.

    Agents are registered by type name and can be instantiated
    from configuration using the registered factory function.
    """

    def __init__(self):
        self._factories: dict[str, Callable[[AgentConfig], BaseAgent]] = {}
        self._types: dict[str, type[BaseAgent]] = {}

    def register(
        self,
        agent_type: str,
        factory: Callable[[AgentConfig], BaseAgent],
        agent_class: type[BaseAgent] | None = None,
    ) -> None:
        """Register an agent type with a factory function.

        Args:
            agent_type: Unique type identifier (e.g. "mock", "openai_compatible").
            factory: Callable that creates an agent from an AgentConfig.
            agent_class: Optional class reference for type checking.
        """
        self._factories[agent_type] = factory
        if agent_class is not None:
            self._types[agent_type] = agent_class

    def unregister(self, agent_type: str) -> None:
        """Remove an agent type from the registry.

        Args:
            agent_type: Type identifier to remove.
        """
        self._factories.pop(agent_type, None)
        self._types.pop(agent_type, None)

    def create(self, config: AgentConfig) -> BaseAgent:
        """Create an agent instance from configuration.

        Args:
            config: Agent configuration.

        Returns:
            Instantiated agent.

        Raises:
            ValueError: If the agent type is not registered.
        """
        factory = self._factories.get(config.agent_type)
        if factory is None:
            available = ", ".join(sorted(self._factories.keys()))
            raise ValueError(f"Unknown agent type: {config.agent_type}. " f"Available types: {available}")
        return factory(config)

    def create_from_dict(self, data: dict[str, Any]) -> BaseAgent:
        """Create an agent from a configuration dictionary.

        Args:
            data: Dictionary with agent configuration.

        Returns:
            Instantiated agent.
        """
        config = AgentConfig.from_dict(data)
        return self.create(config)

    def list_types(self) -> list[str]:
        """List all registered agent types.

        Returns:
            Sorted list of type names.
        """
        return sorted(self._factories.keys())

    def get_type_info(self, agent_type: str) -> dict[str, Any]:
        """Get information about a registered agent type.

        Args:
            agent_type: Type identifier.

        Returns:
            Dictionary with type information.

        Raises:
            ValueError: If the type is not registered.
        """
        if agent_type not in self._factories:
            raise ValueError(f"Unknown agent type: {agent_type}")

        info = {
            "type": agent_type,
            "has_factory": True,
        }
        if agent_type in self._types:
            cls = self._types[agent_type]
            info["class"] = cls.__name__
            info["module"] = cls.__module__
        return info

    def is_registered(self, agent_type: str) -> bool:
        """Check if an agent type is registered.

        Args:
            agent_type: Type identifier.

        Returns:
            True if registered.
        """
        return agent_type in self._factories


# Global registry instance
_default_registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Get the default agent registry.

    Returns:
        The global AgentRegistry instance.
    """
    return _default_registry


def register_agent(
    agent_type: str,
    factory: Callable[[AgentConfig], BaseAgent],
    agent_class: type[BaseAgent] | None = None,
) -> None:
    """Register an agent type with the default registry.

    Args:
        agent_type: Unique type identifier.
        factory: Callable that creates an agent from an AgentConfig.
        agent_class: Optional class reference.
    """
    _default_registry.register(agent_type, factory, agent_class)


# ---------------------------------------------------------------------------
# Auto-registration of built-in agents
# ---------------------------------------------------------------------------


def _register_builtin_agents() -> None:
    """Register all built-in agent types."""
    from forge.agents.mock_agent import MockAgent
    from forge.agents.rule_based import RuleBasedAgent
    from forge.agents.script_agent import ScriptAgent

    # MockAgent
    register_agent(
        "mock",
        lambda config: MockAgent(config, scenario=config.metadata.get("scenario", "success")),
        MockAgent,
    )

    # RuleBasedAgent
    register_agent(
        "rule_based",
        lambda config: RuleBasedAgent(
            config,
            rules=config.metadata.get("rules"),
            rules_file=config.metadata.get("rules_file"),
        ),
        RuleBasedAgent,
    )

    # ScriptAgent
    register_agent(
        "script",
        lambda config: ScriptAgent(
            config,
            script_path=config.metadata.get("script_path", ""),
            timeout=config.metadata.get("timeout", 300),
            extra_env=config.metadata.get("extra_env"),
        ),
        ScriptAgent,
    )

    # OpenAIAgent (optional, requires openai package)
    try:
        from forge.agents.openai_compatible import OpenAIAgent

        register_agent(
            "openai_compatible",
            lambda config: OpenAIAgent(config),
            OpenAIAgent,
        )
    except ImportError:
        pass


# Register built-in agents on module load
_register_builtin_agents()
