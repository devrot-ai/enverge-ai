"""Task variant generator for creating task variations.

Generates variations of existing tasks by combining mutations,
adjusting difficulty, and modifying constraints.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.core.schemas import TaskCategory, TaskSpec, WorldSpec
from forge.world_factory.generator import WorldGenerator


@dataclass
class TaskVariant:
    """A variant of an existing task."""

    task_id: str
    template: str
    mutation: str
    category: str
    description: str
    difficulty: int
    constraints: list[str]
    verification: dict[str, Any]
    capabilities: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_task_spec(self) -> TaskSpec:
        """Convert to a TaskSpec."""
        return TaskSpec(
            task_id=self.task_id,
            world_id=self.metadata.get("world_id", ""),
            description=self.description,
            category=TaskCategory(self.category) if self.category in [
                c.value for c in TaskCategory
            ] else TaskCategory.BUG_REPAIR,
            difficulty_level=self.difficulty,
            constraints=self.constraints,
            verification_method=self.verification.get("method", "test_execution"),
            capabilities=self.capabilities,
            metadata=self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "template": self.template,
            "mutation": self.mutation,
            "category": self.category,
            "description": self.description,
            "difficulty": self.difficulty,
            "constraints": self.constraints,
            "verification": self.verification,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }


class VariantGenerator:
    """Generate task variants from existing templates.

    Creates variations by combining mutations, adjusting difficulty,
    and modifying constraints. Each variant is validated before output.
    """

    # Difficulty modifiers
    difficulty_descriptions = {
        1: "Simple bug with clear error messages",
        2: "Moderate bug requiring basic debugging",
        3: "Complex bug with multiple interacting components",
        4: "Subtle bug requiring deep understanding",
        5: "Extremely subtle bug with misleading symptoms",
    }

    constraint_templates = [
        "Must not modify the public API",
        "Must maintain backward compatibility",
        "Must not add external dependencies",
        "Must pass all existing tests",
        "Must handle edge cases gracefully",
        "Must include error handling",
        "Must preserve performance characteristics",
    ]

    def __init__(self, variants_dir: str | Path | None = None):
        """Initialize the variant generator.

        Args:
            variants_dir: Directory to store generated variants.
        """
        if variants_dir is None:
            self.variants_dir = Path("datasets/variants")
        else:
            self.variants_dir = Path(variants_dir)
        self.world_generator = WorldGenerator()

    def generate_variants(
        self,
        template: str,
        count: int = 5,
        seed: int | None = None,
    ) -> list[TaskVariant]:
        """Generate task variants for a template.

        Args:
            template: Template name (e.g., "task_manager_api").
            count: Number of variants to generate.
            seed: Random seed for reproducibility.

        Returns:
            List of TaskVariant objects.
        """
        if seed is not None:
            random.seed(seed)

        variants = []
        available_mutations = self._get_mutations_for_template(template)

        if not available_mutations:
            return variants

        for i in range(count):
            mutation = random.choice(available_mutations)
            difficulty = random.randint(1, 5)

            # Generate unique task ID
            task_id = f"VARIANT-{template.upper()}-{i+1:03d}"

            # Select random constraints
            num_constraints = random.randint(1, 3)
            constraints = random.sample(
                self.constraint_templates,
                min(num_constraints, len(self.constraint_templates)),
            )

            # Generate capabilities based on template
            capabilities = self._get_capabilities_for_template(template)

            variant = TaskVariant(
                task_id=task_id,
                template=template,
                mutation=mutation,
                category="bug_repair",
                description=self._generate_description(template, mutation, difficulty),
                difficulty=difficulty,
                constraints=constraints,
                verification={
                    "method": "test_execution",
                    "public_tests": True,
                    "hidden_tests": True,
                },
                capabilities=capabilities,
                metadata={
                    "generated_at": datetime.utcnow().isoformat(),
                    "variant_index": i,
                    "seed": seed,
                },
            )
            variants.append(variant)

        # Store variants
        self._store_variants(template, variants)

        return variants

    def generate_world_for_variant(
        self, variant: TaskVariant, seed: int | None = None
    ) -> WorldSpec:
        """Generate a world for a task variant.

        Args:
            variant: The task variant.
            seed: Random seed for world generation.

        Returns:
            WorldSpec for the variant.
        """
        world = self.world_generator.generate(
            template=variant.template,
            mutation=variant.mutation,
            seed=seed or random.randint(10000, 99999),
        )
        return world

    def load_variants(self, template: str) -> list[TaskVariant]:
        """Load previously generated variants for a template.

        Args:
            template: Template name.

        Returns:
            List of TaskVariant objects.
        """
        variants_file = self.variants_dir / f"{template}_variants.json"
        if not variants_file.exists():
            return []

        data = json.loads(variants_file.read_text(encoding="utf-8"))
        variants = []
        for item in data:
            variant = TaskVariant(
                task_id=item["task_id"],
                template=item["template"],
                mutation=item["mutation"],
                category=item["category"],
                description=item["description"],
                difficulty=item["difficulty"],
                constraints=item["constraints"],
                verification=item["verification"],
                capabilities=item["capabilities"],
                metadata=item.get("metadata", {}),
            )
            variants.append(variant)
        return variants

    def _get_mutations_for_template(self, template: str) -> list[str]:
        """Get available mutations for a template.

        Args:
            template: Template name.

        Returns:
            List of mutation names.
        """
        from forge.world_factory.seeder import list_mutations

        all_mutations = list_mutations()
        # Filter mutations by checking if the template's typical mutations exist
        # Since mutations don't have a direct template field, we check by id patterns
        template_mutations = {
            "task_manager_api": ["pagination_boundary", "search_case_sensitive", "filter_logic"],
            "data_pipeline": ["null_handling", "date_parsing", "duplicate_detection", "duplicate_records"],
            "flask_app": ["session_timeout", "password_hash", "csrf_token"],
            "express_api": ["cors_bypass", "rate_limit_off", "input_injection"],
            "django_app": ["sql_injection", "csrf_missing", "open_redirect"],
            "typescript_api": ["error_leak", "input_validation"],
            "go_service": ["nil_pointer", "resource_leak"],
        }
        return template_mutations.get(template, [])

    def _get_capabilities_for_template(self, template: str) -> list[str]:
        """Get capabilities tested by a template.

        Args:
            template: Template name.

        Returns:
            List of capability names.
        """
        capabilities_map = {
            "task_manager_api": ["pagination", "search", "filtering", "error_handling"],
            "data_pipeline": ["validation", "parsing", "transformation", "null_handling"],
            "flask_app": ["authentication", "session_management", "csrf_protection"],
            "express_api": ["routing", "middleware", "cors", "rate_limiting"],
            "django_app": ["orm", "query_building", "csrf", "redirect_validation"],
        }
        return capabilities_map.get(template, ["bug_repair"])

    def _generate_description(
        self, template: str, mutation: str, difficulty: int
    ) -> str:
        """Generate a task description.

        Args:
            template: Template name.
            mutation: Mutation name.
            difficulty: Difficulty level.

        Returns:
            Task description string.
        """
        desc = self.difficulty_descriptions.get(difficulty, "Bug to fix")
        return (
            f"Fix the {mutation} bug in the {template} application. "
            f"Difficulty: {difficulty}/5. {desc}."
        )

    def _store_variants(self, template: str, variants: list[TaskVariant]) -> None:
        """Store variants to disk.

        Args:
            template: Template name.
            variants: List of variants to store.
        """
        self.variants_dir.mkdir(parents=True, exist_ok=True)
        variants_file = self.variants_dir / f"{template}_variants.json"

        data = [v.to_dict() for v in variants]
        variants_file.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
