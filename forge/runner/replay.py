"""Session replay module for analyzing agent trajectories.

Enables replaying agent sessions from exported JSON/JSONL files
for debugging, analysis, and comparison purposes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.core.schemas import (
    RunResult,
    Trajectory,
    TrajectoryStep,
    VerificationResult,
)


@dataclass
class ReplayStep:
    """A single step in a replayed trajectory."""

    step_index: int
    action: str
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    tool_result: str | None = None
    observation: str | None = None
    duration_seconds: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ReplaySession:
    """A complete replayed agent session."""

    task_id: str
    agent_id: str
    passed: bool
    steps: list[ReplayStep] = field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] | None = None
    error: str | None = None


class SessionReplayer:
    """Replay agent trajectories from JSON/JSONL files.

    Loads exported trajectory data and reconstructs sessions
    for analysis without re-running the agent.
    """

    def load(self, file_path: str | Path) -> ReplaySession:
        """Load a single session from a JSON file.

        Args:
            file_path: Path to a JSON file containing trajectory data.

        Returns:
            Reconstructed replay session.
        """
        path = Path(file_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._parse_session(data)

    def load_batch(self, file_path: str | Path) -> list[ReplaySession]:
        """Load multiple sessions from a JSONL file.

        Args:
            file_path: Path to a JSONL file with one session per line.

        Returns:
            List of reconstructed replay sessions.
        """
        path = Path(file_path)
        sessions = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                data = json.loads(line)
                sessions.append(self._parse_session(data))
        return sessions

    def load_directory(self, dir_path: str | Path) -> list[ReplaySession]:
        """Load all JSON/JSONL sessions from a directory.

        Args:
            dir_path: Directory containing trajectory files.

        Returns:
            List of all reconstructed replay sessions.
        """
        path = Path(dir_path)
        sessions = []
        for file_path in sorted(path.glob("*.json")):
            sessions.append(self.load(file_path))
        for file_path in sorted(path.glob("*.jsonl")):
            sessions.extend(self.load_batch(file_path))
        return sessions

    def replay(
        self,
        session: ReplaySession,
        callback: callable | None = None,
    ) -> dict[str, Any]:
        """Replay a session, optionally calling a callback for each step.

        Args:
            session: The replay session to process.
            callback: Optional function called for each step.

        Returns:
            Summary statistics of the replay.
        """
        summary = {
            "task_id": session.task_id,
            "agent_id": session.agent_id,
            "total_steps": len(session.steps),
            "passed": session.passed,
            "duration": session.duration_seconds,
            "tools_used": set(),
            "errors": [],
        }

        for step in session.steps:
            if step.tool_name:
                summary["tools_used"].add(step.tool_name)
            if step.error:
                summary["errors"].append({
                    "step": step.step_index,
                    "error": step.error,
                })
            if callback:
                callback(step)

        summary["tools_used"] = list(summary["tools_used"])
        return summary

    def compare(
        self, session_a: ReplaySession, session_b: ReplaySession
    ) -> dict[str, Any]:
        """Compare two replay sessions side by side.

        Args:
            session_a: First session.
            session_b: Second session.

        Returns:
            Comparison report with differences.
        """
        return {
            "task_id": {
                "a": session_a.task_id,
                "b": session_b.task_id,
            },
            "agent_id": {
                "a": session_a.agent_id,
                "b": session_b.agent_id,
            },
            "passed": {
                "a": session_a.passed,
                "b": session_b.passed,
            },
            "steps": {
                "a": len(session_a.steps),
                "b": len(session_b.steps),
            },
            "duration": {
                "a": session_a.duration_seconds,
                "b": session_b.duration_seconds,
            },
            "tools_used": {
                "a": list({s.tool_name for s in session_a.steps if s.tool_name}),
                "b": list({s.tool_name for s in session_b.steps if s.tool_name}),
            },
            "errors": {
                "a": len([s for s in session_a.steps if s.error]),
                "b": len([s for s in session_b.steps if s.error]),
            },
        }

    def _parse_session(self, data: dict[str, Any]) -> ReplaySession:
        """Parse raw trajectory data into a ReplaySession.

        Args:
            data: Dictionary from JSON/JSONL.

        Returns:
            Reconstructed replay session.
        """
        steps = []
        raw_steps = data.get("steps", [])
        if not raw_steps and "trajectory" in data:
            raw_steps = data["trajectory"].get("steps", [])

        for step_data in raw_steps:
            step = ReplayStep(
                step_index=step_data.get("step_index", len(steps)),
                action=step_data.get("action", ""),
                tool_name=step_data.get("tool_name"),
                tool_arguments=step_data.get("tool_arguments"),
                tool_result=step_data.get("tool_result"),
                observation=step_data.get("observation"),
                duration_seconds=step_data.get("duration_seconds", 0.0),
                error=step_data.get("error"),
                metadata=step_data.get("metadata"),
            )
            steps.append(step)

        # Extract outcome data
        outcome = data.get("final_outcome", {})
        passed = outcome.get("passed", data.get("passed", False))

        # Extract metadata
        task_meta = data.get("task_metadata", {})
        model_meta = data.get("model_metadata", {})

        metadata = {
            **task_meta,
            **model_meta,
            "environment_version": data.get("environment_version"),
            "random_seed": data.get("random_seed"),
        }

        verification = outcome.get("verification")

        return ReplaySession(
            task_id=data.get("task_id", task_meta.get("task_id", "unknown")),
            agent_id=model_meta.get("agent_id", "unknown"),
            passed=bool(passed),
            steps=steps,
            duration_seconds=data.get("duration_seconds", 0.0),
            metadata=metadata,
            verification=verification,
            error=data.get("error"),
        )
