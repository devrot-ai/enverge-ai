"""Composite mutations for multiple bugs per task.

Applies multiple mutations to the same workspace to create
harder, more realistic challenges where the agent must fix
multiple bugs simultaneously.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forge.core.schemas import TaskSpec, TaskCategory, WorldSpec
from forge.world_factory.seeder import MutationPattern

logger = logging.getLogger(__name__)


@dataclass
class CompositeMutation:
    """Multiple mutations applied to the same workspace.

    Contains the list of mutations and validation that they
    don't conflict (e.g., modifying the same line of code).
    """

    template_name: str
    mutation_names: list[str]
    mutations: list[MutationPattern] = field(default_factory=list)
    is_composite: bool = True
    conflict_detected: bool = False
    conflict_details: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "template_name": self.template_name,
            "mutation_names": self.mutation_names,
            "is_composite": self.is_composite,
            "conflict_detected": self.conflict_detected,
            "conflict_details": self.conflict_details,
        }


class CompositeManager:
    """Manage composite mutations with multiple bugs per task.

    Validates that mutations don't conflict and applies them
    in sequence to create realistic multi-bug scenarios.
    """

    def __init__(self):
        """Initialize the composite manager."""
        pass

    def create(
        self,
        template_name: str,
        mutation_names: list[str],
        all_mutations: dict[str, list[MutationPattern]] | None = None,
    ) -> CompositeMutation:
        """Create a composite mutation from multiple mutation names.

        Args:
            template_name: Name of the template.
            mutation_names: List of mutation names to combine.
            all_mutations: Dict of template_name -> list of mutations.

        Returns:
            CompositeMutation with validation results.
        """
        if len(mutation_names) < 2:
            logger.warning(
                f"Composite mutation requires at least 2 mutations, got {len(mutation_names)}"
            )

        # Look up mutation patterns
        mutations: list[MutationPattern] = []
        if all_mutations:
            template_mutations = all_mutations.get(template_name, [])
            mutation_map = {m.name: m for m in template_mutations}

            for name in mutation_names:
                if name in mutation_map:
                    mutations.append(mutation_map[name])
                else:
                    logger.warning(f"Mutation {name} not found for template {template_name}")

        composite = CompositeMutation(
            template_name=template_name,
            mutation_names=mutation_names,
            mutations=mutations,
        )

        # Check for conflicts
        self._check_conflicts(composite)

        return composite

    def _check_conflicts(self, composite: CompositeMutation) -> None:
        """Check if mutations conflict with each other.

        Conflicts occur when two mutations target the same code region.
        We check if search patterns overlap.

        Args:
            composite: Composite mutation to check.
        """
        if len(composite.mutations) < 2:
            return

        conflicts: list[str] = []
        for i, m1 in enumerate(composite.mutations):
            for j, m2 in enumerate(composite.mutations):
                if i >= j:
                    continue
                # Check if search patterns might overlap
                if self._patterns_overlap(m1.search_pattern, m2.search_pattern):
                    conflicts.append(
                        f"Mutations '{m1.name}' and '{m2.name}' may target overlapping code"
                    )

        if conflicts:
            composite.conflict_detected = True
            composite.conflict_details = "; ".join(conflicts)
            logger.warning(
                f"Conflicts detected in composite mutation for {composite.template_name}: "
                f"{composite.conflict_details}"
            )

    def _patterns_overlap(self, pattern1: str, pattern2: str) -> bool:
        """Check if two regex patterns might match overlapping code.

        Simple heuristic: check if patterns share common substrings.

        Args:
            pattern1: First regex pattern.
            pattern2: Second regex pattern.

        Returns:
            True if patterns might overlap.
        """
        # Extract keywords from patterns (alphanumeric sequences)
        keywords1 = set()
        for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]{2,}", pattern1):
            keywords1.add(match.group())

        keywords2 = set()
        for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]{2,}", pattern2):
            keywords2.add(match.group())

        # If they share many keywords, they likely target the same code
        overlap = keywords1 & keywords2
        total = keywords1 | keywords2

        if not total:
            return False

        return len(overlap) / len(total) > 0.5

    def get_compatible_mutations(
        self,
        template_name: str,
        all_mutations: dict[str, list[MutationPattern]],
        max_count: int = 3,
    ) -> list[list[str]]:
        """Get lists of compatible (non-conflicting) mutations for a template.

        Args:
            template_name: Name of the template.
            all_mutations: Dict of template_name -> list of mutations.
            max_count: Maximum number of mutations per composite.

        Returns:
            List of mutation name lists that are compatible.
        """
        template_mutations = all_mutations.get(template_name, [])
        if len(template_mutations) < 2:
            return []

        compatible_sets: list[list[str]] = []

        # Try all pairs
        for i, m1 in enumerate(template_mutations):
            for j, m2 in enumerate(template_mutations):
                if i >= j:
                    continue
                if not self._patterns_overlap(m1.search_pattern, m2.search_pattern):
                    pair = [m1.name, m2.name]
                    compatible_sets.append(pair)

                    # Try adding a third mutation
                    if max_count >= 3:
                        for k, m3 in enumerate(template_mutations):
                            if k <= j:
                                continue
                            if (
                                not self._patterns_overlap(m1.search_pattern, m3.search_pattern)
                                and not self._patterns_overlap(m2.search_pattern, m3.search_pattern)
                            ):
                                compatible_sets.append([m1.name, m2.name, m3.name])

        return compatible_sets

    def apply_composite(
        self,
        content: str,
        composite: CompositeMutation,
    ) -> str | None:
        """Apply all mutations in a composite to the content.

        Args:
            content: Source code content.
            composite: Composite mutation to apply.

        Returns:
            Modified content or None if conflict detected.
        """
        if composite.conflict_detected:
            logger.warning(
                f"Skipping composite mutation due to conflicts: {composite.conflict_details}"
            )
            return None

        new_content = content
        for mutation in composite.mutations:
            if mutation.search_pattern and mutation.replace_with is not None:
                new_content = re.sub(mutation.search_pattern, mutation.replace_with, new_content)

        if new_content == content:
            logger.warning("Composite mutation did not modify content")
            return None

        return new_content

    def create_task_spec(
        self,
        world_spec: WorldSpec,
        composite: CompositeMutation,
        task_id: str,
    ) -> TaskSpec:
        """Create a TaskSpec for a composite mutation task.

        Args:
            world_spec: World specification.
            composite: Composite mutation.
            task_id: Unique task identifier.

        Returns:
            TaskSpec with composite task description.
        """
        # Build description listing all bugs
        bug_descriptions = []
        for mutation in composite.mutations:
            if mutation.description:
                bug_descriptions.append(mutation.description)
            else:
                bug_descriptions.append(f"Bug: {mutation.name}")

        description = (
            f"COMPOSITE TASK: Fix {len(composite.mutation_names)} bugs in the code.\n\n"
            + "\n".join(f"- {desc}" for desc in bug_descriptions)
        )

        # Use maximum difficulty of individual mutations
        difficulty = 1
        for mutation in composite.mutations:
            difficulty = max(difficulty, mutation.difficulty)

        # Combine capabilities
        capabilities: list[str] = []
        for mutation in composite.mutations:
            capabilities.extend(mutation.capabilities)
        capabilities = list(set(capabilities))

        return TaskSpec(
            task_id=task_id,
            world_id=world_spec.world_id,
            description=description,
            category=TaskCategory.BUG_REPAIR,
            difficulty_level=difficulty,
            constraints=getattr(world_spec, 'constraints', []),
            verification_method="test_execution",
            capabilities=capabilities,
            metadata={
                "template_name": composite.template_name,
                "mutation_name": ",".join(composite.mutation_names),
                "is_composite": True,
                "mutation_count": len(composite.mutation_names),
            },
        )
