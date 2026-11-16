"""Cross-template mutation analysis.

Identifies mutation patterns that appear across multiple templates
to help curriculum select tasks that test generalization across domains.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from forge.world_factory.seeder import MutationPattern

logger = logging.getLogger(__name__)


@dataclass
class CrossTemplateResult:
    """Result of cross-template analysis for a mutation pattern."""

    mutation_name: str
    templates: list[str] = field(default_factory=list)
    capability: str = ""
    difficulty: int = 1
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "mutation_name": self.mutation_name,
            "templates": self.templates,
            "capability": self.capability,
            "difficulty": self.difficulty,
            "description": self.description,
        }


class CrossTemplateAnalyzer:
    """Analyze mutation patterns across templates.

    Identifies which capabilities are tested across multiple templates
    and produces a cross-template mutation map for curriculum selection.
    """

    def __init__(self):
        """Initialize the analyzer."""
        pass

    def analyze_mutations(
        self,
        all_mutations: dict[str, list[MutationPattern]],
    ) -> list[CrossTemplateResult]:
        """Analyze mutations across all templates.

        Args:
            all_mutations: Dict of template_name -> list of mutations.

        Returns:
            List of CrossTemplateResult with cross-template mapping.
        """
        # Group mutations by name across templates
        mutation_map: dict[str, list[str]] = {}
        mutation_details: dict[str, dict[str, Any]] = {}

        for template_name, mutations in all_mutations.items():
            for mutation in mutations:
                name = mutation.name
                if name not in mutation_map:
                    mutation_map[name] = []
                    mutation_details[name] = {
                        "capability": mutation.capabilities[0] if mutation.capabilities else "",
                        "difficulty": mutation.difficulty,
                        "description": mutation.description or "",
                    }
                mutation_map[name].append(template_name)

        # Build results
        results = []
        for name, templates in sorted(mutation_map.items()):
            details = mutation_details[name]
            results.append(
                CrossTemplateResult(
                    mutation_name=name,
                    templates=templates,
                    capability=details["capability"],
                    difficulty=details["difficulty"],
                    description=details["description"],
                )
            )

        return results

    def get_cross_template_mutations(
        self,
        all_mutations: dict[str, list[MutationPattern]],
        min_templates: int = 2,
    ) -> list[CrossTemplateResult]:
        """Get mutations that appear in multiple templates.

        Args:
            all_mutations: Dict of template_name -> list of mutations.
            min_templates: Minimum number of templates for inclusion.

        Returns:
            List of mutations appearing in min_templates+ templates.
        """
        results = self.analyze_mutations(all_mutations)
        return [r for r in results if len(r.templates) >= min_templates]

    def get_capability_coverage(
        self,
        all_mutations: dict[str, list[MutationPattern]],
    ) -> dict[str, list[str]]:
        """Get capability coverage across templates.

        Args:
            all_mutations: Dict of template_name -> list of mutations.

        Returns:
            Dict of capability -> list of templates that test it.
        """
        coverage: dict[str, set[str]] = {}

        for template_name, mutations in all_mutations.items():
            for mutation in mutations:
                for capability in mutation.capabilities:
                    if capability not in coverage:
                        coverage[capability] = set()
                    coverage[capability].add(template_name)

        return {k: sorted(v) for k, v in coverage.items()}

    def get_template_coverage(
        self,
        all_mutations: dict[str, list[MutationPattern]],
    ) -> dict[str, dict[str, int]]:
        """Get mutation count per template.

        Args:
            all_mutations: Dict of template_name -> list of mutations.

        Returns:
            Dict of template_name -> {capability: count}.
        """
        coverage: dict[str, dict[str, int]] = {}

        for template_name, mutations in all_mutations.items():
            template_coverage: dict[str, int] = {}
            for mutation in mutations:
                for capability in mutation.capabilities:
                    template_coverage[capability] = template_coverage.get(capability, 0) + 1
            coverage[template_name] = template_coverage

        return coverage

    def generate_report(
        self,
        all_mutations: dict[str, list[MutationPattern]],
    ) -> str:
        """Generate a Markdown report of cross-template analysis.

        Args:
            all_mutations: Dict of template_name -> list of mutations.

        Returns:
            Markdown formatted report.
        """
        lines = ["# Cross-Template Mutation Analysis", ""]

        # Summary
        total_templates = len(all_mutations)
        total_mutations = sum(len(m) for m in all_mutations.values())
        lines.append(f"- **Templates**: {total_templates}")
        lines.append(f"- **Total mutations**: {total_mutations}")
        lines.append("")

        # Cross-template mutations
        cross_template = self.get_cross_template_mutations(all_mutations)
        if cross_template:
            lines.append("## Mutations Across Multiple Templates")
            lines.append("")
            lines.append("| Mutation | Templates | Capability |")
            lines.append("|----------|-----------|------------|")
            for result in cross_template:
                templates = ", ".join(result.templates)
                lines.append(f"| {result.mutation_name} | {templates} | {result.capability} |")
            lines.append("")

        # Capability coverage
        coverage = self.get_capability_coverage(all_mutations)
        lines.append("## Capability Coverage")
        lines.append("")
        lines.append("| Capability | Templates |")
        lines.append("|------------|-----------|")
        for capability, templates in sorted(coverage.items()):
            lines.append(f"| {capability} | {', '.join(templates)} |")
        lines.append("")

        # Template summary
        lines.append("## Template Summary")
        lines.append("")
        for template_name, mutations in sorted(all_mutations.items()):
            lines.append(f"### {template_name}")
            lines.append(f"- **Mutations**: {len(mutations)}")
            caps = set()
            for m in mutations:
                caps.update(m.capabilities)
            lines.append(f"- **Capabilities**: {', '.join(sorted(caps))}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(
        self,
        all_mutations: dict[str, list[MutationPattern]],
    ) -> dict[str, Any]:
        """Serialize analysis results to dictionary.

        Args:
            all_mutations: Dict of template_name -> list of mutations.

        Returns:
            Dictionary with full analysis results.
        """
        return {
            "cross_template_mutations": [
                r.to_dict() for r in self.get_cross_template_mutations(all_mutations)
            ],
            "capability_coverage": self.get_capability_coverage(all_mutations),
            "template_coverage": self.get_template_coverage(all_mutations),
        }
