"""Experiment artifact management.

Provides functions to store, retrieve, and export experiment artifacts
like trajectories, verification results, and reports.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from forge.core.schemas import RunResult


class ArtifactManager:
    """Manages experiment artifacts.

    Stores trajectories, verification results, and reports
    in a structured directory hierarchy.

    Attributes:
        base_dir: Base directory for all artifacts.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store_run_artifacts(
        self,
        run_result: RunResult,
        experiment_id: str | None = None,
    ) -> Path:
        """Store all artifacts for a single run.

        Args:
            run_result: The run result.
            experiment_id: Optional parent experiment ID.

        Returns:
            Path to the artifact directory.
        """
        run_dir = self.base_dir / run_result.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Store run result
        result_file = run_dir / "result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(run_result.to_dict(), f, indent=2, default=str)

        # Store trajectory if available
        if run_result.trajectory:
            traj_file = run_dir / "trajectory.jsonl"
            with open(traj_file, "w", encoding="utf-8") as f:
                header = {
                    "type": "trajectory_header",
                    "run_id": run_result.run_id,
                    "task_id": run_result.task_id,
                    "agent_id": run_result.agent_id,
                }
                f.write(json.dumps(header) + "\n")
                for step in run_result.trajectory.steps:
                    f.write(json.dumps({"type": "step", **step.to_dict()}) + "\n")

        # Store experiment link
        if experiment_id:
            link_file = run_dir / "experiment_id.txt"
            link_file.write_text(experiment_id)

        return run_dir

    def store_batch_artifacts(
        self,
        results: list[RunResult],
        experiment_id: str | None = None,
    ) -> list[Path]:
        """Store artifacts for a batch of runs.

        Args:
            results: List of run results.
            experiment_id: Optional parent experiment ID.

        Returns:
            List of artifact directory paths.
        """
        paths = []
        for result in results:
            path = self.store_run_artifacts(result, experiment_id)
            paths.append(path)
        return paths

    def get_run_artifacts(self, run_id: str) -> Path | None:
        """Get the artifact directory for a run.

        Args:
            run_id: Run identifier.

        Returns:
            Path to artifact directory, or None if not found.
        """
        run_dir = self.base_dir / run_id
        if run_dir.exists():
            return run_dir
        return None

    def list_artifacts(self) -> list[dict[str, Any]]:
        """List all stored artifacts.

        Returns:
            List of artifact metadata dictionaries.
        """
        artifacts = []
        for run_dir in sorted(self.base_dir.iterdir()):
            if run_dir.is_dir():
                result_file = run_dir / "result.json"
                if result_file.exists():
                    with open(result_file, encoding="utf-8") as f:
                        data = json.load(f)
                    artifacts.append(
                        {
                            "run_id": run_dir.name,
                            "task_id": data.get("task_id"),
                            "agent_id": data.get("agent_id"),
                            "status": data.get("status"),
                            "passed": data.get("passed"),
                            "path": str(run_dir),
                        }
                    )
        return artifacts

    def export_experiment_artifacts(
        self,
        experiment_id: str,
        output_dir: Path,
    ) -> Path:
        """Export all artifacts for an experiment.

        Args:
            experiment_id: Experiment identifier.
            output_dir: Directory to export to.

        Returns:
            Path to the exported directory.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        export_dir = output_dir / experiment_id
        export_dir.mkdir(parents=True, exist_ok=True)

        # Find all runs for this experiment
        for run_dir in self.base_dir.iterdir():
            if run_dir.is_dir():
                link_file = run_dir / "experiment_id.txt"
                if link_file.exists() and link_file.read_text().strip() == experiment_id:
                    # Copy run artifacts
                    dest = export_dir / run_dir.name
                    shutil.copytree(run_dir, dest)

        return export_dir

    def cleanup(self, run_id: str) -> bool:
        """Remove artifacts for a run.

        Args:
            run_id: Run identifier.

        Returns:
            True if artifacts were removed.
        """
        run_dir = self.base_dir / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
            return True
        return False
