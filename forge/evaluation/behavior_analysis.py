"""Agent behavior analysis.

Analyzes tool call patterns, failure modes, and agent trajectories
to understand how agents behave across different tasks.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ToolPattern:
    """Pattern of tool usage by an agent."""

    tool_name: str
    call_count: int
    success_count: int
    failure_count: int
    avg_duration_ms: float = 0.0


@dataclass
class FailureMode:
    """A clustered failure mode."""

    category: str
    count: int
    example_task_ids: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class BehaviorProfile:
    """Behavior profile for an agent type."""

    agent_type: str
    total_runs: int = 0
    tool_patterns: List[ToolPattern] = field(default_factory=list)
    failure_modes: List[FailureMode] = field(default_factory=list)
    pass_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "total_runs": self.total_runs,
            "tool_patterns": [
                {
                    "tool": tp.tool_name,
                    "calls": tp.call_count,
                    "successes": tp.success_count,
                    "failures": tp.failure_count,
                    "avg_ms": round(tp.avg_duration_ms, 2),
                }
                for tp in self.tool_patterns
            ],
            "failure_modes": [
                {
                    "category": fm.category,
                    "count": fm.count,
                    "examples": fm.example_task_ids[:5],
                }
                for fm in self.failure_modes
            ],
            "pass_rate": round(self.pass_rate, 3),
        }

    def to_markdown(self) -> str:
        lines = [f"# Behavior Profile: {self.agent_type}", ""]
        lines.append(f"**Total runs:** {self.total_runs}")
        lines.append(f"**Pass rate:** {self.pass_rate:.1%}")
        lines.append("")

        if self.tool_patterns:
            lines.append("## Tool Usage")
            lines.append("")
            lines.append("| Tool | Calls | Success | Failure | Avg (ms) |")
            lines.append("|------|-------|---------|---------|----------|")
            for tp in sorted(self.tool_patterns, key=lambda x: x.call_count, reverse=True):
                lines.append(
                    f"| {tp.tool_name} | {tp.call_count} | {tp.success_count} | "
                    f"{tp.failure_count} | {tp.avg_duration_ms:.1f} |"
                )
            lines.append("")

        if self.failure_modes:
            lines.append("## Failure Modes")
            lines.append("")
            for fm in sorted(self.failure_modes, key=lambda x: x.count, reverse=True):
                lines.append(f"### {fm.category} ({fm.count} occurrences)")
                if fm.description:
                    lines.append(f"{fm.description}")
                if fm.example_task_ids:
                    lines.append(f"Examples: {', '.join(fm.example_task_ids[:3])}")
                lines.append("")

        return "\n".join(lines)


class BehaviorAnalyzer:
    """Analyze agent behavior from trajectories."""

    def __init__(self):
        self._profiles: Dict[str, BehaviorProfile] = {}

    def analyze(
        self, trajectories: List[Dict[str, Any]]
    ) -> Dict[str, BehaviorProfile]:
        """Analyze tool call patterns and failure modes from trajectories.

        Args:
            trajectories: List of trajectory dicts with keys:
                - agent_type: str
                - steps: list of step dicts with tool_name, success, duration_ms
                - passed: bool
                - failure_category: str (optional)
                - task_id: str (optional)

        Returns:
            Dict mapping agent_type to BehaviorProfile.
        """
        # Group by agent type
        by_agent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for traj in trajectories:
            agent_type = traj.get("agent_type", "unknown")
            by_agent[agent_type].append(traj)

        for agent_type, agent_trajs in by_agent.items():
            profile = self._analyze_agent(agent_type, agent_trajs)
            self._profiles[agent_type] = profile

        return dict(self._profiles)

    def _analyze_agent(
        self, agent_type: str, trajectories: List[Dict[str, Any]]
    ) -> BehaviorProfile:
        """Analyze behavior for a single agent type."""
        total = len(trajectories)
        passed = sum(1 for t in trajectories if t.get("passed"))
        pass_rate = passed / total if total > 0 else 0.0

        # Tool patterns
        tool_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "success": 0, "failure": 0, "total_ms": 0.0}
        )
        for traj in trajectories:
            for step in traj.get("steps", []):
                tool = step.get("tool_name", "unknown")
                stats = tool_stats[tool]
                stats["count"] += 1
                if step.get("success"):
                    stats["success"] += 1
                else:
                    stats["failure"] += 1
                stats["total_ms"] += step.get("duration_ms", 0)

        tool_patterns = []
        for tool, stats in tool_stats.items():
            avg_ms = stats["total_ms"] / stats["count"] if stats["count"] > 0 else 0.0
            tool_patterns.append(
                ToolPattern(
                    tool_name=tool,
                    call_count=stats["count"],
                    success_count=stats["success"],
                    failure_count=stats["failure"],
                    avg_duration_ms=avg_ms,
                )
            )

        # Failure modes
        failure_counter: Dict[str, List[str]] = defaultdict(list)
        for traj in trajectories:
            if not traj.get("passed"):
                cat = traj.get("failure_category", "unknown")
                tid = traj.get("task_id", "unknown")
                failure_counter[cat].append(tid)

        failure_modes = []
        for cat, task_ids in failure_counter.items():
            failure_modes.append(
                FailureMode(
                    category=cat,
                    count=len(task_ids),
                    example_task_ids=list(set(task_ids))[:5],
                    description=f"Tasks failing due to {cat}",
                )
            )

        return BehaviorProfile(
            agent_type=agent_type,
            total_runs=total,
            tool_patterns=tool_patterns,
            failure_modes=failure_modes,
            pass_rate=pass_rate,
        )

    def get_tool_patterns(self, agent_type: str) -> List[ToolPattern]:
        """Get tool usage patterns for an agent.

        Args:
            agent_type: The agent to look up.

        Returns:
            List of ToolPattern sorted by call count.
        """
        profile = self._profiles.get(agent_type)
        if profile is None:
            return []
        return sorted(profile.tool_patterns, key=lambda x: x.call_count, reverse=True)

    def get_failure_modes(self, agent_type: str) -> List[FailureMode]:
        """Get failure modes for an agent.

        Args:
            agent_type: The agent to look up.

        Returns:
            List of FailureMode sorted by count.
        """
        profile = self._profiles.get(agent_type)
        if profile is None:
            return []
        return sorted(profile.failure_modes, key=lambda x: x.count, reverse=True)
