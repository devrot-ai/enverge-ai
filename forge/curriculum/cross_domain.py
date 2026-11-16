"""Cross-domain curriculum with knowledge transfer.

Enables curriculum that tracks multiple template domains simultaneously
and transfers knowledge between them when an agent excels in one domain.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Optional

from forge.core.schemas import RunResult, TaskSpec
from forge.curriculum.selector import CurriculumSelector
from forge.world_factory.cross_template import CrossTemplateAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class DomainState:
    """Per-domain capability tracking."""

    domain: str
    total_runs: int = 0
    passed_runs: int = 0
    pass_rate: float = 0.0
    difficulty: int = 1
    last_task_id: Optional[str] = None

    def update(self, passed: bool) -> None:
        """Update domain state after a run.

        Args:
            passed: Whether the run passed.
        """
        self.total_runs += 1
        if passed:
            self.passed_runs += 1
        self.pass_rate = self.passed_runs / self.total_runs if self.total_runs > 0 else 0.0


class CrossDomainCurriculum:
    """Curriculum that transfers knowledge across template domains.

    Tracks per-domain capability scores and introduces similar patterns
    in other domains when an agent excels in one domain.
    """

    def __init__(
        self,
        transfer_strategy: str = "similar_pattern",
        min_runs_before_transfer: int = 5,
    ):
        """Initialize the cross-domain curriculum.

        Args:
            transfer_strategy: Strategy for knowledge transfer.
                'none' = no transfer, 'similar_pattern' = transfer similar mutation patterns,
                'random' = random domain selection.
            min_runs_before_transfer: Minimum runs in a domain before transfer.
        """
        self.domains: dict[str, DomainState] = {}
        self.transfer_strategy = transfer_strategy
        self.min_runs_before_transfer = min_runs_before_transfer
        self.analyzer = CrossTemplateAnalyzer()
        self.selectors: dict[str, CurriculumSelector] = {}

    def add_domain(self, domain: str) -> None:
        """Add a new template domain to track.

        Args:
            domain: Template name (e.g., 'task_manager_api').
        """
        if domain not in self.domains:
            self.domains[domain] = DomainState(domain=domain)
            self.selectors[domain] = CurriculumSelector(strategy="adaptive")
            logger.info(f"Added domain: {domain}")

    def select_task(self, agent_type: str, domain: Optional[str] = None) -> Optional[TaskSpec]:
        """Select a task for the given agent, optionally from a specific domain.

        Args:
            agent_type: Type of agent running.
            domain: Optional domain to select from. If None, uses cross-domain logic.

        Returns:
            TaskSpec or None if no tasks available.
        """
        if domain and domain in self.selectors:
            task = self.selectors[domain].select_task(agent_type)
            if task:
                self.domains[domain].last_task_id = task.task_id
            return task

        # Cross-domain selection: pick domain based on transfer strategy
        if self.transfer_strategy == "similar_pattern":
            return self._select_similar_pattern(agent_type)
        elif self.transfer_strategy == "random":
            return self._select_random(agent_type)
        else:
            # 'none' strategy: round-robin
            return self._select_round_robin(agent_type)

    def update(self, domain: str, result: RunResult) -> None:
        """Update domain state after a run.

        Args:
            domain: Domain that was tested.
            result: Run result.
        """
        if domain in self.domains:
            self.domains[domain].update(result.passed)
            logger.info(
                f"Domain {domain}: pass_rate={self.domains[domain].pass_rate:.2f}, "
                f"total={self.domains[domain].total_runs}"
            )

    def _select_similar_pattern(self, agent_type: str) -> Optional[TaskSpec]:
        """Select task from a domain with similar mutation patterns.

        When an agent excels in one domain, introduce similar patterns in another.

        Args:
            agent_type: Type of agent running.

        Returns:
            TaskSpec or None.
        """
        # Find domains where agent has high pass rate
        excelling = [
            d for d, state in self.domains.items()
            if state.total_runs >= self.min_runs_before_transfer and state.pass_rate >= 0.8
        ]

        if excelling:
            # Pick a random excelling domain and try cross-template analysis
            source_domain = random.choice(excelling)
            try:
                cross_map = self.analyzer.get_cross_template_mutations()
                # Find a domain that shares mutation patterns
                for other_domain in self.selectors.keys():
                    if other_domain != source_domain and other_domain in cross_map:
                        return self.selectors[other_domain].select_task(agent_type)
            except Exception:
                pass

        # Fallback: pick any domain
        return self._select_random(agent_type)

    def _select_random(self, agent_type: str) -> Optional[TaskSpec]:
        """Select task from a random domain.

        Args:
            agent_type: Type of agent running.

        Returns:
            TaskSpec or None.
        """
        if not self.selectors:
            return None
        domain = random.choice(list(self.selectors.keys()))
        return self.selectors[domain].select_task(agent_type)

    def _select_round_robin(self, agent_type: str) -> Optional[TaskSpec]:
        """Select task using round-robin across domains.

        Args:
            agent_type: Type of agent running.

        Returns:
            TaskSpec or None.
        """
        if not self.selectors:
            return None
        # Pick domain with fewest runs
        domain = min(self.domains.keys(), key=lambda d: self.domains[d].total_runs)
        return self.selectors[domain].select_task(agent_type)

    def get_domain_summary(self) -> dict[str, Any]:
        """Get summary of all domain states.

        Returns:
            Dict with domain names as keys and state dicts as values.
        """
        return {
            domain: {
                "total_runs": state.total_runs,
                "passed_runs": state.passed_runs,
                "pass_rate": state.pass_rate,
                "difficulty": state.difficulty,
            }
            for domain, state in self.domains.items()
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dict representation.
        """
        return {
            "transfer_strategy": self.transfer_strategy,
            "min_runs_before_transfer": self.min_runs_before_transfer,
            "domains": self.get_domain_summary(),
        }
