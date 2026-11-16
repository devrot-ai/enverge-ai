"""Export run data from SQLite database as JSON and CSV.

Enables researchers to analyze results in external tools.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forge.db.models import RunRecord, TaskRecord, WorldRecord


def export_runs(
    db_url: str,
    format: str = "json",
    output: Path | None = None,
    run_ids: list[str] | None = None,
) -> str:
    """Export run data from the database.

    Args:
        db_url: SQLAlchemy database URL (e.g., sqlite:///./forgelab.db).
        format: Output format: "json" or "csv".
        output: Output file path. If None, returns the data as a string.
        run_ids: Optional list of run IDs to filter. If None, exports all runs.

    Returns:
        The exported data as a string (or path if written to file).
    """
    engine = create_engine(db_url)
    with Session(engine) as session:
        runs = _load_runs(session, run_ids)
    engine.dispose()

    if format == "json":
        data = _format_json(runs)
    elif format == "csv":
        data = _format_csv(runs)
    else:
        raise ValueError(f"Unsupported format: {format}")

    if output:
        output.write_text(data, encoding="utf-8")
        return str(output)
    return data


def _load_runs(session: Session, run_ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Load runs with related tasks and worlds.

    Args:
        session: SQLAlchemy session.
        run_ids: Optional list of run IDs to filter.

    Returns:
        List of run records with related data.
    """
    query = session.query(RunRecord)
    if run_ids:
        query = query.filter(RunRecord.run_id.in_(run_ids))
    runs = query.all()

    result = []
    for run in runs:
        task = session.query(TaskRecord).filter_by(task_id=run.task_id).first()
        world = session.query(WorldRecord).filter_by(world_id=task.world_id if task else None).first()

        result.append(
            {
                "run_id": run.run_id,
                "task_id": run.task_id,
                "agent_id": run.agent_id,
                "passed": bool(run.passed),
                "duration_seconds": run.duration_seconds,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "trajectory": run.trajectory_json or {},
                "task": (
                    {
                        "task_id": task.task_id,
                        "world_id": task.world_id,
                        "category": task.category,
                        "description": task.description,
                        "difficulty_level": task.difficulty_level,
                    }
                    if task
                    else None
                ),
                "world": (
                    {
                        "world_id": world.world_id,
                        "template_name": world.template_name,
                        "mutation_id": world.mutation_id,
                    }
                    if world
                    else None
                ),
            }
        )

    return result


def _format_json(runs: list[dict[str, Any]]) -> str:
    """Format runs as JSON.

    Args:
        runs: List of run records.

    Returns:
        JSON string.
    """
    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "total_runs": len(runs),
        "runs": runs,
    }
    return json.dumps(data, indent=2, default=str)


def _format_csv(runs: list[dict[str, Any]]) -> str:
    """Format runs as CSV.

    Args:
        runs: List of run records.

    Returns:
        CSV string.
    """
    import io

    output = io.StringIO()
    if not runs:
        return ""

    fieldnames = [
        "run_id",
        "task_id",
        "agent_id",
        "passed",
        "duration_seconds",
        "status",
        "started_at",
        "finished_at",
        "task_category",
        "task_description",
        "task_difficulty",
        "world_template",
        "world_mutation",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    for run in runs:
        row = {
            "run_id": run["run_id"],
            "task_id": run["task_id"],
            "agent_id": run["agent_id"],
            "passed": run["passed"],
            "duration_seconds": run["duration_seconds"],
            "status": run["status"],
            "started_at": run["started_at"],
            "finished_at": run["finished_at"],
        }
        if run.get("task"):
            row["task_category"] = run["task"].get("category")
            row["task_description"] = run["task"].get("description")
            row["task_difficulty"] = run["task"].get("difficulty_level")
        if run.get("world"):
            row["world_template"] = run["world"].get("template_name")
            row["world_mutation"] = run["world"].get("mutation_id")
        writer.writerow(row)

    return output.getvalue()
