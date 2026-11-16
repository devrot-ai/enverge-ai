"""Custom experiment definitions.

Enable YAML-based custom experiment definitions beyond presets,
supporting single agent, multi-agent, A/B test, and benchmark suite experiments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class CustomExperiment:
    """A user-defined experiment loaded from YAML.

    YAML schema:
        name: str
        description: str
        type: single_agent | multi_agent | ab_test | benchmark
        agents:
          - type: str
            config: dict
        tasks:
          source: seed | heldout | custom
          count: int
        parameters:
          max_steps: int
          timeout: float
        metrics:
          - pass_rate
          - duration
          - failure_category
        comparison_method: pass_rate | duration | custom
    """

    name: str
    description: str = ""
    experiment_type: str = "single_agent"
    agents: list[dict[str, Any]] = field(default_factory=list)
    tasks: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    metrics: list[str] = field(default_factory=list)
    comparison_method: str = "pass_rate"
    raw_yaml: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, yaml_path: str | Path) -> CustomExperiment:
        """Load a custom experiment from a YAML file.

        Args:
            yaml_path: Path to the YAML experiment definition.

        Returns:
            CustomExperiment instance.

        Raises:
            FileNotFoundError: If the YAML file doesn't exist.
            ValueError: If the YAML is invalid.
        """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Experiment file not found: {path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid experiment YAML: {path}")

        return cls(
            name=raw.get("name", path.stem),
            description=raw.get("description", ""),
            experiment_type=raw.get("type", "single_agent"),
            agents=raw.get("agents", []),
            tasks=raw.get("tasks", {}),
            parameters=raw.get("parameters", {}),
            metrics=raw.get("metrics", ["pass_rate"]),
            comparison_method=raw.get("comparison_method", "pass_rate"),
            raw_yaml=raw,
        )

    def validate(self) -> list[str]:
        """Validate the experiment definition.

        Returns:
            List of validation errors. Empty if valid.
        """
        errors = []

        if not self.name:
            errors.append("Experiment name is required")

        if self.experiment_type not in ("single_agent", "multi_agent", "ab_test", "benchmark"):
            errors.append(f"Invalid experiment type: {self.experiment_type}")

        if self.experiment_type in ("single_agent", "ab_test", "benchmark"):
            if not self.agents:
                errors.append("At least one agent is required")

        if self.experiment_type == "ab_test" and len(self.agents) < 2:
            errors.append("A/B test requires at least 2 agents")

        if not self.tasks:
            errors.append("Task source is required")
        else:
            if self.tasks.get("source") not in ("seed", "heldout", "custom", None):
                errors.append(f"Invalid task source: {self.tasks.get('source')}")

        if not self.metrics:
            errors.append("At least one metric is required")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dict representation of the experiment.
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": self.experiment_type,
            "agents": self.agents,
            "tasks": self.tasks,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "comparison_method": self.comparison_method,
        }

    def save(self, yaml_path: str | Path) -> None:
        """Save the experiment definition to a YAML file.

        Args:
            yaml_path: Output path for the YAML file.
        """
        path = Path(yaml_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.dump(self.to_dict(), default_flow_style=False), encoding="utf-8")


class CustomExperimentLoader:
    """Load and manage custom experiment definitions.

    Scans a directory for YAML experiment files and provides
    validation and loading.
    """

    def __init__(self, experiments_dir: str | Path | None = None):
        """Initialize the loader.

        Args:
            experiments_dir: Directory containing experiment YAML files.
        """
        self.experiments_dir = Path(experiments_dir) if experiments_dir else None
        self.experiments: dict[str, CustomExperiment] = {}

    def load(self, yaml_path: str | Path) -> CustomExperiment:
        """Load a single experiment from YAML.

        Args:
            yaml_path: Path to the YAML file.

        Returns:
            CustomExperiment instance.
        """
        exp = CustomExperiment.load(yaml_path)
        self.experiments[exp.name] = exp
        return exp

    def load_directory(self, directory: str | Path | None = None) -> list[CustomExperiment]:
        """Load all experiments from a directory.

        Args:
            directory: Directory to scan. Uses default if None.

        Returns:
            List of loaded CustomExperiment instances.
        """
        dir_path = Path(directory) if directory else self.experiments_dir
        if dir_path is None:
            return []

        loaded = []
        for yaml_file in sorted(dir_path.glob("*.yaml")):
            try:
                exp = self.load(yaml_file)
                loaded.append(exp)
            except Exception as e:
                logger.warning("Failed to load %s: %s", yaml_file.name, e)

        return loaded

    def get(self, name: str) -> CustomExperiment | None:
        """Get a loaded experiment by name.

        Args:
            name: Experiment name.

        Returns:
            CustomExperiment or None.
        """
        return self.experiments.get(name)

    def list_experiments(self) -> list[dict[str, str]]:
        """List all loaded experiments.

        Returns:
            List of dicts with name and description.
        """
        return [
            {"name": name, "description": exp.description, "type": exp.experiment_type}
            for name, exp in self.experiments.items()
        ]

    def validate_all(self) -> dict[str, list[str]]:
        """Validate all loaded experiments.

        Returns:
            Dict of experiment name -> list of errors.
        """
        results = {}
        for name, exp in self.experiments.items():
            errors = exp.validate()
            if errors:
                results[name] = errors
        return results
