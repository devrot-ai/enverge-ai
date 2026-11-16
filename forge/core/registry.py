"""Registry system for ForgeLab components.

Provides centralized registration and lookup for templates, agents,
generators, validators, and other pluggable components.
"""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


class Registry:
    """Generic registry for pluggable components.

    Components are registered by name and optionally tagged with metadata.
    The registry supports lookup by name, listing all registered components,
    and filtering by tags.

    Example:
        >>> registry = Registry("agents")
        >>> registry.register("mock", MockAgent)
        >>> agent_cls = registry.get("mock")
    """

    def __init__(self, name: str):
        self.name = name
        self._items: dict[str, Any] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        obj: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a component by name.

        Args:
            name: Unique identifier for this component.
            obj: The component object or class.
            metadata: Optional metadata for filtering and discovery.
        """
        self._items[name] = obj
        self._metadata[name] = metadata or {}

    def get(self, name: str) -> Any | None:
        """Look up a component by name.

        Args:
            name: The component name.

        Returns:
            The registered component, or None if not found.
        """
        return self._items.get(name)

    def exists(self, name: str) -> bool:
        """Check if a component is registered.

        Args:
            name: The component name.

        Returns:
            True if the component is registered.
        """
        return name in self._items

    def list_all(self) -> list[str]:
        """List all registered component names.

        Returns:
            Sorted list of registered names.
        """
        return sorted(self._items.keys())

    def list_with_metadata(self) -> list[dict[str, Any]]:
        """List all components with their metadata.

        Returns:
            List of dicts with 'name', 'metadata' keys.
        """
        result = []
        for name in self.list_all():
            result.append(
                {
                    "name": name,
                    "metadata": self._metadata.get(name, {}),
                }
            )
        return result

    def filter_by_tag(self, tag_key: str, tag_value: Any) -> list[str]:
        """Filter registered components by metadata tag.

        Args:
            tag_key: Metadata key to filter on.
            tag_value: Value to match.

        Returns:
            List of component names matching the tag.
        """
        return [name for name, meta in self._metadata.items() if meta.get(tag_key) == tag_value]

    def unregister(self, name: str) -> bool:
        """Remove a component from the registry.

        Args:
            name: The component name.

        Returns:
            True if the component was found and removed.
        """
        if name in self._items:
            del self._items[name]
            del self._metadata[name]
            return True
        return False

    def __contains__(self, name: str) -> bool:
        return self.exists(name)

    def __len__(self) -> int:
        return len(self._items)


# ---------------------------------------------------------------------------
# Global registries
# ---------------------------------------------------------------------------

# World template registry
world_templates: Registry = Registry("world_templates")

# Agent registry
agents: Registry = Registry("agents")

# Task generator registry
task_generators: Registry = Registry("task_generators")

# Validator registry
validators: Registry = Registry("validators")

# Verifier registry
verifiers: Registry = Registry("verifiers")

# Curriculum strategy registry
curriculum_strategies: Registry = Registry("curriculum_strategies")
