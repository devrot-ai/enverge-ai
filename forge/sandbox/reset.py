"""Workspace reset and cleanup utilities.

Provides functions to reset workspaces to their initial state
and clean up temporary files after runs.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def reset_workspace(workspace: Path) -> bool:
    """Reset a workspace to its initial git state.

    Discards all changes and resets to the initial commit.

    Args:
        workspace: Path to the workspace directory.

    Returns:
        True if reset succeeded.
    """
    try:
        # Discard all changes
        subprocess.run(
            ["git", "checkout", "--", "."],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Clean untracked files
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def cleanup_workspace(workspace: Path) -> bool:
    """Remove a workspace directory entirely.

    Args:
        workspace: Path to the workspace directory.

    Returns:
        True if cleanup succeeded.
    """
    try:
        if workspace.exists():
            shutil.rmtree(workspace)
        return True
    except OSError:
        return False


def create_fresh_workspace(
    source: Path,
    destination: Path,
) -> bool:
    """Create a fresh copy of a workspace from a source.

    Args:
        source: Source directory to copy from.
        destination: Destination directory.

    Returns:
        True if copy succeeded.
    """
    try:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        return True
    except (OSError, shutil.Error):
        return False


def get_workspace_size(workspace: Path) -> int:
    """Get the total size of a workspace in bytes.

    Args:
        workspace: Path to the workspace directory.

    Returns:
        Total size in bytes.
    """
    total = 0
    if not workspace.exists():
        return 0
    for dirpath, dirnames, filenames in workspace.walk():
        for f in filenames:
            fp = Path(dirpath) / f
            if fp.is_file():
                total += fp.stat().st_size
    return total


def list_workspace_files(workspace: Path) -> list:
    """List all files in a workspace.

    Args:
        workspace: Path to the workspace directory.

    Returns:
        List of relative file paths.
    """
    if not workspace.exists():
        return []
    files = []
    for dirpath, dirnames, filenames in workspace.walk():
        for f in filenames:
            fp = Path(dirpath) / f
            files.append(str(fp.relative_to(workspace)))
    return sorted(files)
