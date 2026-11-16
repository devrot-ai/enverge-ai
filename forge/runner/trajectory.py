"""Trajectory recording and export utilities.

Provides functions to save, load, and export agent execution
trajectories in JSONL format for analysis and debugging.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.core.schemas import Trajectory, TrajectoryStep


def save_trajectory(trajectory: Trajectory, directory: Path) -> Path:
    """Save a trajectory to a JSONL file.

    Args:
        trajectory: The trajectory to save.
        directory: Directory to save the file in.

    Returns:
        Path to the saved file.
    """
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{trajectory.run_id}.jsonl"
    filepath = directory / filename

    with open(filepath, "w", encoding="utf-8") as f:
        # Write header
        header = {
            "type": "trajectory_header",
            "trajectory_id": trajectory.trajectory_id,
            "run_id": trajectory.run_id,
            "task_id": trajectory.task_id,
            "agent_id": trajectory.agent_id,
            "started_at": trajectory.started_at,
            "finished_at": trajectory.finished_at,
            "termination_reason": trajectory.termination_reason,
            "total_duration_seconds": trajectory.total_duration_seconds,
            "total_token_usage": trajectory.total_token_usage,
        }
        f.write(json.dumps(header) + "\n")

        # Write each step
        for step in trajectory.steps:
            step_data = {
                "type": "step",
                **step.to_dict(),
            }
            f.write(json.dumps(step_data) + "\n")

    return filepath


def load_trajectory(filepath: Path) -> Trajectory:
    """Load a trajectory from a JSONL file.

    Args:
        filepath: Path to the JSONL file.

    Returns:
        Reconstructed Trajectory object.
    """
    header = None
    steps = []

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("type") == "trajectory_header":
                header = data
            elif data.get("type") == "step":
                steps.append(TrajectoryStep.from_dict(data))

    if header is None:
        raise ValueError(f"No header found in trajectory file: {filepath}")

    traj = Trajectory(
        trajectory_id=header.get("trajectory_id"),
        run_id=header["run_id"],
        task_id=header["task_id"],
        agent_id=header["agent_id"],
    )
    traj.started_at = header.get("started_at", traj.started_at)
    traj.finished_at = header.get("finished_at")
    traj.termination_reason = header.get("termination_reason")
    traj.total_duration_seconds = header.get("total_duration_seconds", 0.0)
    traj.total_token_usage = header.get("total_token_usage", {})

    for step in steps:
        traj.add_step(step)

    return traj


def list_trajectories(directory: Path) -> list[dict[str, Any]]:
    """List all trajectories in a directory.

    Args:
        directory: Directory containing trajectory files.

    Returns:
        List of trajectory metadata dictionaries.
    """
    if not directory.exists():
        return []

    trajectories = []
    for filepath in sorted(directory.glob("*.jsonl")):
        try:
            with open(filepath, encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line:
                    data = json.loads(first_line)
                    data["file_path"] = str(filepath)
                    trajectories.append(data)
        except (OSError, json.JSONDecodeError):
            continue

    return trajectories


def export_trajectory_summary(trajectory: Trajectory) -> dict[str, Any]:
    """Export a summary of a trajectory for reporting.

    Args:
        trajectory: The trajectory to summarize.

    Returns:
        Dictionary with trajectory summary.
    """
    tool_calls = {}
    errors = 0
    total_duration = 0.0

    for step in trajectory.steps:
        if step.tool_name:
            tool_calls[step.tool_name] = tool_calls.get(step.tool_name, 0) + 1
        if step.error:
            errors += 1
        total_duration += step.duration_seconds

    return {
        "trajectory_id": trajectory.trajectory_id,
        "run_id": trajectory.run_id,
        "task_id": trajectory.task_id,
        "agent_id": trajectory.agent_id,
        "total_steps": len(trajectory.steps),
        "total_duration_seconds": trajectory.total_duration_seconds,
        "termination_reason": trajectory.termination_reason,
        "tool_calls": tool_calls,
        "errors": errors,
        "token_usage": trajectory.total_token_usage,
        "started_at": trajectory.started_at,
        "finished_at": trajectory.finished_at,
    }


def filter_trajectory_steps(
    trajectory: Trajectory,
    tool_name: str | None = None,
    has_error: bool = False,
) -> list[TrajectoryStep]:
    """Filter trajectory steps by criteria.

    Args:
        trajectory: The trajectory to filter.
        tool_name: Only include steps with this tool name.
        has_error: Only include steps with errors.

    Returns:
        Filtered list of steps.
    """
    filtered = []
    for step in trajectory.steps:
        if tool_name and step.tool_name != tool_name:
            continue
        if has_error and not step.error:
            continue
        filtered.append(step)
    return filtered
