"""MLflow integration for experiment tracking.

Optional MLflow tracking for experiment results. Falls back to
SQLite-only if MLflow is not installed. Configurable via
FORGELAB_MLFLOW_TRACKING_URI environment variable.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MLflowRunResult:
    """Result of logging to MLflow."""

    success: bool = False
    run_id: str = ""
    experiment_id: str = ""
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "details": self.details,
        }


class MLflowTracker:
    """Optional MLflow tracking for experiment results.

    Integrates with ExperimentManager to log results to MLflow.
    Falls back to no-op if MLflow is not installed.

    Usage:
        tracker = MLflowTracker(tracking_uri="http://localhost:5000")
        tracker.log_experiment("my_experiment")
        tracker.log_metric("pass_rate", 0.75)
        tracker.log_artifact("report.json")
    """

    def __init__(self, tracking_uri: str | None = None):
        """Initialize the MLflow tracker.

        Args:
            tracking_uri: MLflow tracking URI. Uses env var if None.
        """
        self.tracking_uri = tracking_uri or os.environ.get("FORGELAB_MLFLOW_TRACKING_URI")
        self._mlflow_available = False
        self._mlflow = None
        self._current_run_id = ""
        self._current_experiment_id = ""
        self._metrics: dict[str, float] = {}
        self._params: dict[str, Any] = {}
        self._artifacts: list[str] = []

        # Try to import mlflow
        try:
            import mlflow as _mlflow

            self._mlflow = _mlflow
            self._mlflow_available = True

            if self.tracking_uri:
                _mlflow.set_tracking_uri(self.tracking_uri)
                logger.info("MLflow tracking enabled: %s", self.tracking_uri)
            else:
                logger.info("MLflow available but no tracking URI set")
        except ImportError:
            logger.info("MLflow not installed; tracking disabled")

    @property
    def is_available(self) -> bool:
        """Check if MLflow is available.

        Returns:
            True if MLflow is installed and configured.
        """
        return self._mlflow_available

    def log_experiment(self, experiment_name: str) -> MLflowRunResult:
        """Start or resume an MLflow experiment.

        Args:
            experiment_name: Name of the experiment.

        Returns:
            MLflowRunResult with status.
        """
        if not self._mlflow_available:
            return MLflowRunResult(
                success=False,
                details="MLflow not available",
            )

        try:
            self._current_experiment_id = self._mlflow.create_experiment(
                experiment_name,
                artifacts_uri=f"file://{Path.cwd()}/mlflow_artifacts",
            )
            self._mlflow.set_experiment(experiment_name)
            run = self._mlflow.start_run()
            self._current_run_id = run.info.run_id

            return MLflowRunResult(
                success=True,
                run_id=self._current_run_id,
                experiment_id=self._current_experiment_id,
                details=f"Started run in experiment '{experiment_name}'",
            )
        except Exception as e:
            return MLflowRunResult(
                success=False,
                details=f"Failed to start experiment: {e}",
            )

    def log_run(self, run_name: str, params: dict[str, Any] | None = None) -> MLflowRunResult:
        """Log a new run within the current experiment.

        Args:
            run_name: Name of the run.
            params: Optional parameters to log.

        Returns:
            MLflowRunResult with status.
        """
        if not self._mlflow_available:
            return MLflowRunResult(
                success=False,
                details="MLflow not available",
            )

        try:
            if params:
                for key, value in params.items():
                    self._mlflow.log_param(key, value)
                    self._params[key] = value

            return MLflowRunResult(
                success=True,
                run_id=self._current_run_id,
                details=f"Logged run '{run_name}'",
            )
        except Exception as e:
            return MLflowRunResult(
                success=False,
                details=f"Failed to log run: {e}",
            )

    def log_metric(self, key: str, value: float) -> MLflowRunResult:
        """Log a metric to the current run.

        Args:
            key: Metric name.
            value: Metric value.

        Returns:
            MLflowRunResult with status.
        """
        self._metrics[key] = value

        if not self._mlflow_available:
            return MLflowRunResult(
                success=False,
                details="MLflow not available",
            )

        try:
            self._mlflow.log_metric(key, value)
            return MLflowRunResult(
                success=True,
                details=f"Logged metric {key}={value}",
            )
        except Exception as e:
            return MLflowRunResult(
                success=False,
                details=f"Failed to log metric: {e}",
            )

    def log_artifact(self, artifact_path: str | Path) -> MLflowRunResult:
        """Log an artifact file to the current run.

        Args:
            artifact_path: Path to the artifact file.

        Returns:
            MLflowRunResult with status.
        """
        self._artifacts.append(str(artifact_path))

        if not self._mlflow_available:
            return MLflowRunResult(
                success=False,
                details="MLflow not available",
            )

        try:
            self._mlflow.log_artifact(str(artifact_path))
            return MLflowRunResult(
                success=True,
                details=f"Logged artifact: {artifact_path}",
            )
        except Exception as e:
            return MLflowRunResult(
                success=False,
                details=f"Failed to log artifact: {e}",
            )

    def end_run(self) -> None:
        """End the current MLflow run."""
        if self._mlflow_available:
            try:
                self._mlflow.end_run()
            except Exception as e:
                logger.warning("Failed to end MLflow run: %s", e)
        self._current_run_id = ""

    def get_metrics(self) -> dict[str, float]:
        """Get all logged metrics.

        Returns:
            Dict of metric name -> value.
        """
        return dict(self._metrics)

    def get_params(self) -> dict[str, Any]:
        """Get all logged parameters.

        Returns:
            Dict of param name -> value.
        """
        return dict(self._params)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary.

        Returns:
            Dict with tracking status and data.
        """
        return {
            "available": self._mlflow_available,
            "tracking_uri": self.tracking_uri,
            "run_id": self._current_run_id,
            "experiment_id": self._current_experiment_id,
            "metrics": self._metrics,
            "params": self._params,
            "artifacts": self._artifacts,
        }
