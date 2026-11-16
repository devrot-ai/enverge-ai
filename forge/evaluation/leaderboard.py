"""Benchmark leaderboard for tracking agent performance over time.

Stores benchmark results and generates rankings comparing agent
performance across templates, difficulties, and time periods.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardEntry:
    """A single entry in the leaderboard."""

    run_id: str
    agent_type: str
    task_id: str
    template: str
    difficulty: int
    passed: bool
    duration_seconds: float
    failure_category: str | None
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "run_id": self.run_id,
            "agent_type": self.agent_type,
            "task_id": self.task_id,
            "template": self.template,
            "difficulty": self.difficulty,
            "passed": self.passed,
            "duration_seconds": round(self.duration_seconds, 2),
            "failure_category": self.failure_category,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LeaderboardEntry:
        """Deserialize from dictionary."""
        return cls(
            run_id=data["run_id"],
            agent_type=data["agent_type"],
            task_id=data["task_id"],
            template=data["template"],
            difficulty=data["difficulty"],
            passed=data["passed"],
            duration_seconds=data["duration_seconds"],
            failure_category=data.get("failure_category"),
            timestamp=data["timestamp"],
        )


@dataclass
class AgentRanking:
    """Ranking summary for an agent."""

    agent_type: str
    total_runs: int = 0
    passed: int = 0
    failed: int = 0
    avg_duration: float = 0.0
    templates: dict[str, int] = field(default_factory=dict)
    difficulties: dict[int, int] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.total_runs == 0:
            return 0.0
        return self.passed / self.total_runs

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_type": self.agent_type,
            "total_runs": self.total_runs,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 4),
            "avg_duration": round(self.avg_duration, 2),
            "templates": self.templates,
            "difficulties": {str(k): v for k, v in self.difficulties.items()},
        }


class Leaderboard:
    """Track and compare agent performance over time.

    Stores results in a JSON file and generates rankings and
    comparison reports.
    """

    def __init__(self, data_file: str | Path | None = None):
        """Initialize the leaderboard.

        Args:
            data_file: Path to the leaderboard data file.
        """
        if data_file is None:
            self.data_file = Path("leaderboard.json")
        else:
            self.data_file = Path(data_file)
        self._entries: list[LeaderboardEntry] = []
        self._load()

    def add_result(self, entry: LeaderboardEntry) -> None:
        """Add a benchmark result to the leaderboard.

        Args:
            entry: The leaderboard entry to add.
        """
        self._entries.append(entry)
        self._save()

    def add_results(self, entries: list[LeaderboardEntry]) -> None:
        """Add multiple benchmark results.

        Args:
            entries: List of leaderboard entries.
        """
        self._entries.extend(entries)
        self._save()

    def get_rankings(
        self,
        agent_type: str | None = None,
        template: str | None = None,
    ) -> list[AgentRanking]:
        """Get agent rankings sorted by pass rate.

        Args:
            agent_type: Optional filter by agent type.
            template: Optional filter by template.

        Returns:
            List of AgentRanking sorted by pass rate (descending).
        """
        entries = self._entries

        if agent_type:
            entries = [e for e in entries if e.agent_type == agent_type]
        if template:
            entries = [e for e in entries if e.template == template]

        # Group by agent type
        agent_data: dict[str, list[LeaderboardEntry]] = {}
        for entry in entries:
            if entry.agent_type not in agent_data:
                agent_data[entry.agent_type] = []
            agent_data[entry.agent_type].append(entry)

        rankings = []
        for agent_type, agent_entries in agent_data.items():
            ranking = AgentRanking(agent_type=agent_type)
            total_duration = 0.0

            for entry in agent_entries:
                ranking.total_runs += 1
                total_duration += entry.duration_seconds
                if entry.passed:
                    ranking.passed += 1
                else:
                    ranking.failed += 1

                # Track by template
                if entry.template not in ranking.templates:
                    ranking.templates[entry.template] = 0
                ranking.templates[entry.template] += 1

                # Track by difficulty
                if entry.difficulty not in ranking.difficulties:
                    ranking.difficulties[entry.difficulty] = 0
                ranking.difficulties[entry.difficulty] += 1

            ranking.avg_duration = (
                total_duration / ranking.total_runs if ranking.total_runs else 0.0
            )
            rankings.append(ranking)

        # Sort by pass rate descending
        rankings.sort(key=lambda r: r.pass_rate, reverse=True)
        return rankings

    def compare_agents(
        self, agent_types: list[str], template: str | None = None
    ) -> dict[str, Any]:
        """Compare multiple agents side by side.

        Args:
            agent_types: List of agent types to compare.
            template: Optional filter by template.

        Returns:
            Comparison dictionary.
        """
        rankings = self.get_rankings(template=template)

        # Filter to requested agent types
        rankings = [r for r in rankings if r.agent_type in agent_types]

        return {
            "agent_count": len(rankings),
            "template_filter": template,
            "rankings": [r.to_dict() for r in rankings],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_entries(
        self,
        agent_type: str | None = None,
        template: str | None = None,
        passed: bool | None = None,
    ) -> list[LeaderboardEntry]:
        """Query leaderboard entries.

        Args:
            agent_type: Optional filter by agent type.
            template: Optional filter by template.
            passed: Optional filter by pass/fail.

        Returns:
            List of matching entries.
        """
        entries = self._entries

        if agent_type:
            entries = [e for e in entries if e.agent_type == agent_type]
        if template:
            entries = [e for e in entries if e.template == template]
        if passed is not None:
            entries = [e for e in entries if e.passed == passed]

        return entries

    def export(self, output_file: str | Path | None = None) -> str:
        """Export leaderboard as JSON string.

        Args:
            output_file: Optional file to write to.

        Returns:
            JSON string of the leaderboard data.
        """
        data = {
            "entry_count": len(self._entries),
            "entries": [e.to_dict() for e in self._entries],
            "exported_at": datetime.utcnow().isoformat(),
        }

        json_str = json.dumps(data, indent=2, default=str)

        if output_file:
            Path(output_file).write_text(json_str, encoding="utf-8")
            logger.info(f"Exported leaderboard to: {output_file}")

        return json_str

    def to_markdown(self) -> str:
        """Generate a Markdown leaderboard table.

        Returns:
            Markdown formatted leaderboard.
        """
        rankings = self.get_rankings()

        lines = ["# Benchmark Leaderboard", ""]
        lines.append(
            f"**Total Entries:** {len(self._entries)} | "
            f"**Agents:** {len(rankings)}"
        )
        lines.append("")
        lines.append(
            "| Rank | Agent | Runs | Passed | Failed | Pass Rate | Avg Duration |"
        )
        lines.append(
            "|------|-------|------|--------|--------|-----------|--------------|"
        )

        for i, ranking in enumerate(rankings, 1):
            lines.append(
                f"| {i} | {ranking.agent_type} | {ranking.total_runs} "
                f"| {ranking.passed} | {ranking.failed} "
                f"| {ranking.pass_rate:.1%} | {ranking.avg_duration:.1f}s |"
            )

        lines.append("")
        return "\n".join(lines)

    def _load(self) -> None:
        """Load entries from disk."""
        if not self.data_file.exists():
            return

        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self._entries = [
                LeaderboardEntry.from_dict(entry) for entry in data.get("entries", [])
            ]
        except (json.JSONDecodeError, KeyError):
            self._entries = []

    def _save(self) -> None:
        """Save entries to disk."""
        data = {
            "entries": [e.to_dict() for e in self._entries],
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.data_file.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
