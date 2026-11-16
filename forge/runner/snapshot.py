"""Workspace snapshot and restore for reproducibility.

Captures workspace file contents as JSON for later restoration,
enabling re-verification of agent outputs and debugging.
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class WorkspaceSnapshot:
    """A snapshot of a workspace at a point in time."""

    run_id: str
    timestamp: float
    file_contents: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceSnapshot":
        return cls(**data)


class WorkspaceSnapshotter:
    """Capture and restore workspace states for reproducibility."""

    def __init__(self, snapshot_dir: str = "snapshots"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, workspace_dir: str, run_id: str = "") -> WorkspaceSnapshot:
        """Capture all files in a workspace directory as a snapshot.

        Args:
            workspace_dir: Path to the workspace to capture.
            run_id: Optional run identifier for the snapshot.

        Returns:
            WorkspaceSnapshot with all file contents.
        """
        ws = Path(workspace_dir)
        if not ws.exists():
            raise FileNotFoundError(f"Workspace not found: {workspace_dir}")

        file_contents = {}
        for root, dirs, files in os.walk(ws):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in files:
                fpath = Path(root) / fname
                rel_path = str(fpath.relative_to(ws)).replace("\\", "/")
                try:
                    content = fpath.read_text(encoding="utf-8")
                    file_contents[rel_path] = content
                except (UnicodeDecodeError, PermissionError):
                    # Skip binary or inaccessible files
                    pass

        snapshot = WorkspaceSnapshot(
            run_id=run_id or "unknown",
            timestamp=time.time(),
            file_contents=file_contents,
            metadata={"workspace_dir": str(ws.resolve()), "file_count": len(file_contents)},
        )
        return snapshot

    def save(self, snapshot: WorkspaceSnapshot) -> str:
        """Save a snapshot to disk as JSON.

        Args:
            snapshot: The snapshot to save.

        Returns:
            Path to the saved snapshot file.
        """
        timestamp_str = int(snapshot.timestamp * 1000)  # milliseconds
        filename = f"{snapshot.run_id}_{timestamp_str}.json"
        filepath = self.snapshot_dir / filename

        filepath.write_text(
            json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(filepath)

    def restore(self, snapshot_path: str, restore_dir: str) -> int:
        """Restore a workspace from a snapshot file.

        Args:
            snapshot_path: Path to the saved snapshot JSON file.
            restore_dir: Directory to restore files into.

        Returns:
            Number of files restored.
        """
        sp = Path(snapshot_path)
        if not sp.exists():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")

        data = json.loads(sp.read_text(encoding="utf-8"))
        snapshot = WorkspaceSnapshot.from_dict(data)

        rd = Path(restore_dir)
        rd.mkdir(parents=True, exist_ok=True)

        count = 0
        for rel_path, content in snapshot.file_contents.items():
            fpath = rd / rel_path
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")
            count += 1

        return count

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all saved snapshots.

        Returns:
            List of snapshot metadata dicts sorted by timestamp (newest first).
        """
        snapshots = []
        for fpath in sorted(self.snapshot_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(fpath.read_text(encoding="utf-8"))
                snapshots.append(
                    {
                        "file": str(fpath),
                        "run_id": data.get("run_id", "unknown"),
                        "timestamp": data.get("timestamp", 0),
                        "file_count": len(data.get("file_contents", {})),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return snapshots
