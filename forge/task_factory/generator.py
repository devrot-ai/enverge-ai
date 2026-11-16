"""Task factory: generates structured task specifications.

Creates TaskSpec objects from world specifications and mutation metadata.
Supports loading seed tasks from YAML files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from forge.core.schemas import TaskCategory, TaskSpec, WorldSpec
from forge.world_factory.seeder import get_mutation


class TaskGenerator:
    """Generates task specifications from worlds and mutations.

    Maps world mutations to human-readable task descriptions
    with appropriate constraints and verification settings.
    """

    def generate_from_world(
        self,
        world_spec: WorldSpec,
        task_id: str | None = None,
    ) -> TaskSpec:
        """Generate a task spec from a world specification.

        Args:
            world_spec: The world this task operates on.
            task_id: Optional pre-assigned task ID.

        Returns:
            TaskSpec for the generated task.
        """
        mutation = get_mutation(world_spec.mutation_id or "")
        if mutation is None:
            # Fallback generic task
            return TaskSpec(
                task_id=task_id,
                world_id=world_spec.world_id,
                category=TaskCategory.BUG_REPAIR,
                description=f"Fix a bug in the {world_spec.template_name} codebase.",
                capabilities=["debugging"],
            )

        # Map mutation to task category
        category = self._map_category(mutation)
        description = self._generate_description(mutation, world_spec)
        capabilities = mutation.get("capabilities", ["debugging"])
        difficulty = mutation.get("difficulty", 2)

        return TaskSpec(
            task_id=task_id,
            world_id=world_spec.world_id,
            category=category,
            description=description,
            constraints=["preserve_existing_api", "preserve_existing_functionality"],
            verification_method="isolated_hidden_pytest",
            require_existing_tests=True,
            difficulty_level=difficulty,
            capabilities=capabilities,
            metadata={
                "mutation_id": world_spec.mutation_id,
                "template_name": world_spec.template_name,
            },
        )

    def _map_category(self, mutation: dict[str, Any]) -> TaskCategory:
        """Map a mutation to a task category."""
        desc = (mutation.get("description", "") + mutation.get("name", "")).lower()
        if "edge" in desc or "boundary" in desc:
            return TaskCategory.EDGE_CASE_DEBUGGING
        elif "regression" in desc:
            return TaskCategory.REGRESSION_REPAIR
        else:
            return TaskCategory.BUG_REPAIR

    def _generate_description(self, mutation: dict[str, Any], world_spec: WorldSpec) -> str:
        """Generate a human-readable task description."""
        name = mutation.get("name", "Bug")
        desc = mutation.get("description", "")

        # Create the agent-facing description
        return (
            f"Fix the following bug in the {world_spec.template_name} codebase:\n\n"
            f"{desc}\n\n"
            f"You have access to the source code, public tests, and can run tests "
            f"to verify your changes. The fix should not break existing functionality."
        )

    def generate_variant(
        self,
        base_task: TaskSpec,
        variation: str,
        task_id: str | None = None,
    ) -> TaskSpec:
        """Generate a variant of an existing task.

        Args:
            base_task: The base task to vary.
            variation: Description of the variation.
            task_id: Optional pre-assigned task ID.

        Returns:
            New TaskSpec with the variation.
        """
        return TaskSpec(
            task_id=task_id,
            world_id=base_task.world_id,
            category=base_task.category,
            description=f"{base_task.description}\n\nVariation: {variation}",
            constraints=base_task.constraints,
            verification_method=base_task.verification_method,
            require_existing_tests=base_task.require_existing_tests,
            difficulty_level=base_task.difficulty_level + 1,
            capabilities=base_task.capabilities,
            metadata={
                "base_task_id": base_task.task_id,
                "variation": variation,
                **(base_task.metadata or {}),
            },
        )

    def load_seed_tasks(self, seed_file: str) -> list[TaskSpec]:
        """Load seed tasks from a YAML file.

        Args:
            seed_file: Path to the YAML seed tasks file.

        Returns:
            List of TaskSpec objects loaded from the file.
        """
        seed_path = Path(seed_file)
        if not seed_path.exists():
            return []

        with open(seed_path) as f:
            data = yaml.safe_load(f)

        if not data or "seeds" not in data:
            return []

        tasks: list[TaskSpec] = []
        for item in data["seeds"]:
            category_str = item.get("category", "bug_repair")
            try:
                category = TaskCategory(category_str)
            except ValueError:
                category = TaskCategory.BUG_REPAIR

            # Extract verification settings from nested verification key
            verification = item.get("verification", {})
            if isinstance(verification, dict):
                verification_method = verification.get("method", "isolated_hidden_pytest")
                require_existing_tests = verification.get("require_existing_tests", True)
            else:
                verification_method = item.get("verification_method", "isolated_hidden_pytest")
                require_existing_tests = item.get("require_existing_tests", True)

            task = TaskSpec(
                task_id=item.get("task_id"),
                world_id="",
                category=category,
                description=item.get("description", ""),
                constraints=item.get("constraints", []),
                verification_method=verification_method,
                require_existing_tests=require_existing_tests,
                difficulty_level=item.get("difficulty", 2),
                capabilities=item.get("capabilities", ["debugging"]),
                metadata={
                    "seed": True,
                    "source_file": str(seed_path),
                    "template": item.get("template", ""),
                    "mutation": item.get("mutation", ""),
                },
            )
            tasks.append(task)

        return tasks
