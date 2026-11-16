"""Mutation coverage analysis.

Identifies which mutations are tested by which tasks and worlds,
and finds gaps in mutation coverage across the task pool.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class MutationCoverageReport:
    """Report of mutation coverage across tasks."""

    mutation_to_tasks: Dict[str, List[str]] = field(default_factory=dict)
    uncovered_mutations: List[str] = field(default_factory=list)
    total_mutations: int = 0
    covered_mutations: int = 0
    coverage_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_to_tasks": self.mutation_to_tasks,
            "uncovered_mutations": self.uncovered_mutations,
            "total_mutations": self.total_mutations,
            "covered_mutations": self.covered_mutations,
            "coverage_percent": self.coverage_percent,
        }

    def to_markdown(self) -> str:
        lines = ["# Mutation Coverage Report", ""]
        lines.append(f"**Coverage:** {self.covered_mutations}/{self.total_mutations} "
                      f"({self.coverage_percent:.1f}%)")
        lines.append("")
        lines.append("## Covered Mutations")
        lines.append("")
        lines.append("| Mutation | Tasks |")
        lines.append("|----------|-------|")
        for mut, tasks in sorted(self.mutation_to_tasks.items()):
            lines.append(f"| {mut} | {', '.join(tasks)} |")
        lines.append("")

        if self.uncovered_mutations:
            lines.append("## Uncovered Mutations")
            lines.append("")
            for mut in self.uncovered_mutations:
                lines.append(f"- {mut}")
            lines.append("")

        return "\n".join(lines)


class MutationCoverageAnalyzer:
    """Analyze which mutations are covered by the task pool."""

    def __init__(self, seeder_module=None, task_factory_dir: Optional[str] = None):
        self.seeder = seeder_module
        self.task_factory_dir = task_factory_dir
        self._report: Optional[MutationCoverageReport] = None

    def analyze(self, all_mutations: Optional[List[str]] = None,
                task_specs: Optional[List[Any]] = None) -> MutationCoverageReport:
        """Analyze mutation coverage from task specs.

        Args:
            all_mutations: List of all known mutation names. If None, loaded from seeder.
            task_specs: List of task spec objects with `mutation` attribute.

        Returns:
            MutationCoverageReport with coverage details.
        """
        # Get all mutations
        if all_mutations is None:
            if self.seeder and hasattr(self.seeder, "list_mutations"):
                all_mutations = self.seeder.list_mutations()
            else:
                all_mutations = []

        # Get mutations from tasks
        mutation_to_tasks: Dict[str, Set[str]] = {}
        if task_specs:
            for task in task_specs:
                mut = getattr(task, "mutation", None)
                task_id = getattr(task, "task_id", getattr(task, "id", "unknown"))
                if mut:
                    if mut not in mutation_to_tasks:
                        mutation_to_tasks[mut] = set()
                    mutation_to_tasks[mut].add(task_id)

        # Build report
        mutation_to_task_lists = {
            mut: sorted(tasks) for mut, tasks in mutation_to_tasks.items()
        }
        covered = set(mutation_to_tasks.keys())
        all_set = set(all_mutations)
        uncovered = sorted(all_set - covered)

        total = len(all_set) if all_set else len(mutation_to_tasks)
        covered_count = len(covered)
        pct = (covered_count / total * 100) if total > 0 else 0.0

        self._report = MutationCoverageReport(
            mutation_to_tasks=mutation_to_task_lists,
            uncovered_mutations=uncovered,
            total_mutations=total,
            covered_mutations=covered_count,
            coverage_percent=pct,
        )
        return self._report

    def get_coverage(self, mutation_name: str) -> List[str]:
        """Get the list of tasks covering a specific mutation.

        Args:
            mutation_name: The mutation to look up.

        Returns:
            List of task IDs that test this mutation.
        """
        if self._report is None:
            return []
        return self._report.mutation_to_tasks.get(mutation_name, [])

    def get_gaps(self) -> List[str]:
        """Get mutations with no task coverage.

        Returns:
            List of uncovered mutation names.
        """
        if self._report is None:
            return []
        return list(self._report.uncovered_mutations)
