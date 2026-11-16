"""Dataset versioning for training data reproducibility.

Enables creating versioned snapshots of training datasets so experiments
can be reproduced with the exact same data. Each version stores a manifest
with metadata and the actual data as JSONL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DatasetVersion:
    """A versioned snapshot of a training dataset."""

    version_tag: str
    created_at: str
    num_examples: int = 0
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DatasetVersion:
        """Deserialize from dictionary."""
        return cls(**data)


class DatasetVersioner:
    """Manage versioned training datasets.

    Creates versioned snapshots stored in `datasets/versions/` with
    a manifest.json describing each version and the data as JSONL.
    """

    def __init__(self, versions_dir: str | Path | None = None):
        """Initialize the versioner.

        Args:
            versions_dir: Directory to store versions. Defaults to
                `datasets/versions/` in the current working directory.
        """
        if versions_dir is None:
            self.versions_dir = Path("datasets/versions")
        else:
            self.versions_dir = Path(versions_dir)

    def create_version(
        self,
        tag: str,
        examples: list[dict[str, Any]],
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> DatasetVersion:
        """Create a new versioned dataset.

        Args:
            tag: Version tag (e.g., "v1.0", "experiment-a").
            examples: List of example dictionaries to store.
            description: Human-readable description.
            metadata: Additional metadata for the version.

        Returns:
            The created DatasetVersion.
        """
        version_dir = self.versions_dir / tag
        version_dir.mkdir(parents=True, exist_ok=True)

        # Write data as JSONL
        data_file = version_dir / "data.jsonl"
        with open(data_file, "w", encoding="utf-8") as f:
            for example in examples:
                f.write(json.dumps(example, default=str) + "\n")

        # Create manifest
        version = DatasetVersion(
            version_tag=tag,
            created_at=datetime.utcnow().isoformat(),
            num_examples=len(examples),
            description=description,
            metadata=metadata or {},
        )

        manifest_file = version_dir / "manifest.json"
        manifest_file.write_text(
            json.dumps(version.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

        return version

    def list_versions(self) -> list[DatasetVersion]:
        """List all available versions.

        Returns:
            List of DatasetVersion for each version directory.
        """
        if not self.versions_dir.exists():
            return []

        versions = []
        for version_dir in sorted(self.versions_dir.iterdir()):
            if version_dir.is_dir():
                manifest_file = version_dir / "manifest.json"
                if manifest_file.exists():
                    data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    versions.append(DatasetVersion.from_dict(data))
        return versions

    def load_version(self, tag: str) -> list[dict[str, Any]]:
        """Load examples from a specific version.

        Args:
            tag: Version tag to load.

        Returns:
            List of example dictionaries.

        Raises:
            FileNotFoundError: If version does not exist.
        """
        data_file = self.versions_dir / tag / "data.jsonl"
        if not data_file.exists():
            raise FileNotFoundError(f"Version not found: {tag}")

        examples = []
        for line in data_file.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                examples.append(json.loads(line))
        return examples

    def diff_versions(
        self, tag_a: str, tag_b: str
    ) -> dict[str, Any]:
        """Compare two versions and return the differences.

        Args:
            tag_a: First version tag.
            tag_b: Second version tag.

        Returns:
            Dictionary with version info and differences.
        """
        versions_a = self.list_versions()
        version_a = next((v for v in versions_a if v.version_tag == tag_a), None)
        version_b = next((v for v in versions_a if v.version_tag == tag_b), None)

        if version_a is None:
            raise FileNotFoundError(f"Version not found: {tag_a}")
        if version_b is None:
            raise FileNotFoundError(f"Version not found: {tag_b}")

        examples_a = self.load_version(tag_a)
        examples_b = self.load_version(tag_b)

        return {
            "version_a": {
                "tag": tag_a,
                "num_examples": len(examples_a),
                "created_at": version_a.created_at,
            },
            "version_b": {
                "tag": tag_b,
                "num_examples": len(examples_b),
                "created_at": version_b.created_at,
            },
            "diff": {
                "example_count_diff": len(examples_b) - len(examples_a),
                "examples_added": max(0, len(examples_b) - len(examples_a)),
                "examples_removed": max(0, len(examples_a) - len(examples_b)),
            },
        }
