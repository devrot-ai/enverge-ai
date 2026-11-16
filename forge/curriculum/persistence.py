"""Curriculum persistence for saving and loading state.

Enables saving and loading curriculum state for cross-session
experiments. Stores capability tracker state, history, and selected
tasks as JSON.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.core.schemas import CurriculumState, CurriculumStrategy

logger = logging.getLogger(__name__)


@dataclass
class CurriculumSnapshot:
    """A snapshot of curriculum state at a point in time."""

    curriculum_id: str
    strategy: str
    capability_scores: dict[str, float]
    selected_tasks: list[str]
    history: list[dict[str, Any]]
    saved_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "curriculum_id": self.curriculum_id,
            "strategy": self.strategy,
            "capability_scores": self.capability_scores,
            "selected_tasks": self.selected_tasks,
            "history": self.history,
            "saved_at": self.saved_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CurriculumSnapshot:
        """Deserialize from dictionary."""
        return cls(
            curriculum_id=data["curriculum_id"],
            strategy=data["strategy"],
            capability_scores=data["capability_scores"],
            selected_tasks=data["selected_tasks"],
            history=data["history"],
            saved_at=data["saved_at"],
            metadata=data.get("metadata", {}),
        )


class CurriculumPersistence:
    """Save and load curriculum state for cross-session experiments.

    Stores capability tracker state, history, and selected tasks as JSON
    files that can be version-controlled and shared.
    """

    def __init__(self, persist_dir: str | Path | None = None):
        """Initialize the persistence manager.

        Args:
            persist_dir: Directory to store curriculum snapshots.
        """
        if persist_dir is None:
            self.persist_dir = Path("curriculum_state")
        else:
            self.persist_dir = Path(persist_dir)

    def save(
        self,
        curriculum: CurriculumState,
        snapshot_name: str | None = None,
    ) -> Path:
        """Save curriculum state to disk.

        Args:
            curriculum: The curriculum state to save.
            snapshot_name: Optional name for the snapshot. Defaults to
                timestamp-based name.

        Returns:
            Path to the saved snapshot file.
        """
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        if snapshot_name is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            snapshot_name = f"curriculum_{timestamp}"

        snapshot = CurriculumSnapshot(
            curriculum_id=curriculum.curriculum_id,
            strategy=curriculum.strategy.value
            if isinstance(curriculum.strategy, CurriculumStrategy)
            else curriculum.strategy,
            capability_scores=curriculum.capability_scores or {},
            selected_tasks=list(curriculum.selected_tasks) if curriculum.selected_tasks else [],
            history=[],
            saved_at=datetime.utcnow().isoformat(),
            metadata={
                "num_selected_tasks": len(curriculum.selected_tasks) if curriculum.selected_tasks else 0,
            },
        )

        snapshot_file = self.persist_dir / f"{snapshot_name}.json"
        snapshot_file.write_text(
            json.dumps(snapshot.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

        logger.info(f"Saved curriculum snapshot: {snapshot_file}")
        return snapshot_file

    def load(self, snapshot_name: str) -> CurriculumSnapshot:
        """Load a curriculum snapshot from disk.

        Args:
            snapshot_name: Name of the snapshot (without .json extension).

        Returns:
            CurriculumSnapshot object.

        Raises:
            FileNotFoundError: If the snapshot doesn't exist.
        """
        snapshot_file = self.persist_dir / f"{snapshot_name}.json"
        if not snapshot_file.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_file}")

        data = json.loads(snapshot_file.read_text(encoding="utf-8"))
        return CurriculumSnapshot.from_dict(data)

    def load_to_state(self, snapshot_name: str) -> CurriculumState:
        """Load a curriculum snapshot and convert to CurriculumState.

        Args:
            snapshot_name: Name of the snapshot.

        Returns:
            CurriculumState object.
        """
        snapshot = self.load(snapshot_name)

        strategy = CurriculumStrategy(snapshot.strategy)
        if isinstance(strategy, str):
            try:
                strategy = CurriculumStrategy(snapshot.strategy)
            except ValueError:
                strategy = CurriculumStrategy.ADAPTIVE

        return CurriculumState(
            curriculum_id=snapshot.curriculum_id,
            strategy=strategy,
            capability_scores=snapshot.capability_scores,
            selected_tasks=snapshot.selected_tasks,
        )

    def list_snapshots(self) -> list[dict[str, Any]]:
        """List all available curriculum snapshots.

        Returns:
            List of snapshot metadata dictionaries.
        """
        if not self.persist_dir.exists():
            return []

        snapshots = []
        for snapshot_file in sorted(self.persist_dir.glob("*.json")):
            try:
                data = json.loads(snapshot_file.read_text(encoding="utf-8"))
                snapshots.append(
                    {
                        "name": snapshot_file.stem,
                        "curriculum_id": data.get("curriculum_id"),
                        "strategy": data.get("strategy"),
                        "saved_at": data.get("saved_at"),
                        "num_selected_tasks": data.get("metadata", {}).get(
                            "num_selected_tasks", 0
                        ),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        return snapshots

    def export(
        self,
        curriculum: CurriculumState,
        output_file: str | Path,
    ) -> Path:
        """Export curriculum state to a specific file.

        Args:
            curriculum: The curriculum state to export.
            output_file: Output file path.

        Returns:
            Path to the exported file.
        """
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        snapshot = CurriculumSnapshot(
            curriculum_id=curriculum.curriculum_id,
            strategy=curriculum.strategy.value
            if isinstance(curriculum.strategy, CurriculumStrategy)
            else curriculum.strategy,
            capability_scores=curriculum.capability_scores or {},
            selected_tasks=list(curriculum.selected_tasks) if curriculum.selected_tasks else [],
            history=[],
            saved_at=datetime.utcnow().isoformat(),
        )

        output_file.write_text(
            json.dumps(snapshot.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

        logger.info(f"Exported curriculum to: {output_file}")
        return output_file

    def import_(self, input_file: str | Path) -> CurriculumState:
        """Import curriculum state from a file.

        Args:
            input_file: Input file path.

        Returns:
            CurriculumState object.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        input_file = Path(input_file)
        if not input_file.exists():
            raise FileNotFoundError(f"File not found: {input_file}")

        data = json.loads(input_file.read_text(encoding="utf-8"))
        snapshot = CurriculumSnapshot.from_dict(data)

        strategy = CurriculumStrategy(snapshot.strategy)
        if isinstance(strategy, str):
            try:
                strategy = CurriculumStrategy(snapshot.strategy)
            except ValueError:
                strategy = CurriculumStrategy.ADAPTIVE

        return CurriculumState(
            curriculum_id=snapshot.curriculum_id,
            strategy=strategy,
            capability_scores=snapshot.capability_scores,
            selected_tasks=snapshot.selected_tasks,
        )
