"""Manifest: world metadata tracking.

Each generated world has a manifest file (.forgelab_manifest.json)
that records how it was created for reproducibility and debugging.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_manifest(world_dir: Path) -> dict[str, Any] | None:
    """Read the ForgeLab manifest from a world directory.

    Args:
        world_dir: Path to the world directory.

    Returns:
        Manifest dictionary or None if not found.
    """
    manifest_path = world_dir / ".forgelab_manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text())


def write_manifest(world_dir: Path, manifest: dict[str, Any]) -> None:
    """Write a manifest to a world directory.

    Args:
        world_dir: Path to the world directory.
        manifest: Manifest dictionary.
    """
    manifest_path = world_dir / ".forgelab_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))


def has_manifest(world_dir: Path) -> bool:
    """Check if a world directory has a manifest.

    Args:
        world_dir: Path to the world directory.

    Returns:
        True if manifest exists.
    """
    return (world_dir / ".forgelab_manifest.json").exists()
