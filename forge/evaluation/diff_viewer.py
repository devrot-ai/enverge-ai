"""Code diff viewer for agent workspace changes.

Compares the original workspace code with the agent's modified version
to show what changes the agent made.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiffHunk:
    """A single hunk of changes in a file diff.

    Attributes:
        filename: Path to the file being diffed.
        added_lines: Lines added by the agent.
        removed_lines: Lines removed by the agent.
        context_before: Context lines before the change.
        context_after: Context lines after the change.
        start_line: Starting line number in the original file.
    """

    filename: str
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    start_line: int = 0


@dataclass
class FileDiff:
    """Diff result for a single file.

    Attributes:
        filename: Path to the file.
        changed: Whether the file was modified.
        hunks: List of change hunks.
        added_count: Number of lines added.
        removed_count: Number of lines removed.
        original_content: Original file content.
        modified_content: Modified file content (agent's version).
    """

    filename: str
    changed: bool = False
    hunks: list[DiffHunk] = field(default_factory=list)
    added_count: int = 0
    removed_count: int = 0
    original_content: str = ""
    modified_content: str = ""


@dataclass
class WorkspaceDiff:
    """Diff result for an entire workspace.

    Attributes:
        files: List of file diffs.
        total_added: Total lines added across all files.
        total_removed: Total lines removed across all files.
        files_changed: Number of files that were modified.
    """

    files: list[FileDiff] = field(default_factory=list)
    total_added: int = 0
    total_removed: int = 0
    files_changed: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "files": [
                {
                    "filename": f.filename,
                    "changed": f.changed,
                    "added": f.added_count,
                    "removed": f.removed_count,
                    "hunks": [
                        {
                            "added_lines": h.added_lines,
                            "removed_lines": h.removed_lines,
                            "start_line": h.start_line,
                        }
                        for h in f.hunks
                    ],
                }
                for f in self.files
            ],
            "total_added": self.total_added,
            "total_removed": self.total_removed,
            "files_changed": self.files_changed,
        }


class DiffViewer:
    """Computes diffs between original and modified workspace code.

    Compares files from the original world template with the agent's
    modified workspace to show exactly what changes were made.
    """

    def __init__(self):
        pass

    def diff_workspaces(
        self,
        original_dir: Path,
        modified_dir: Path,
        patterns: list[str] | None = None,
    ) -> WorkspaceDiff:
        """Compute the diff between original and modified workspaces.

        Args:
            original_dir: Path to the original (pre-mutation) workspace.
            modified_dir: Path to the agent's modified workspace.
            patterns: File patterns to include (e.g., ["*.py"]). If None,
                      all files are compared.

        Returns:
            WorkspaceDiff with per-file and summary statistics.
        """
        workspace_diff = WorkspaceDiff()
        original_files = self._get_files(original_dir, patterns)
        modified_files = self._get_files(modified_dir, patterns)
        all_files = set(original_files) | set(modified_files)

        for rel_path in sorted(all_files):
            orig_file = original_dir / rel_path
            mod_file = modified_dir / rel_path

            orig_content = orig_file.read_text() if orig_file.exists() else ""
            mod_content = mod_file.read_text() if mod_file.exists() else ""

            file_diff = self._diff_files(str(rel_path), orig_content, mod_content)
            workspace_diff.files.append(file_diff)

            if file_diff.changed:
                workspace_diff.files_changed += 1
                workspace_diff.total_added += file_diff.added_count
                workspace_diff.total_removed += file_diff.removed_count

        return workspace_diff

    def diff_content(
        self,
        filename: str,
        original: str,
        modified: str,
    ) -> FileDiff:
        """Compute the diff between two content strings.

        Useful when you have the content in memory (e.g., from trajectory data)
        rather than from files on disk.

        Args:
            filename: Name of the file for display purposes.
            original: Original content.
            modified: Modified content.

        Returns:
            FileDiff with hunks and statistics.
        """
        return self._diff_files(filename, original, modified)

    def _diff_files(self, filename: str, original: str, modified: str) -> FileDiff:
        """Compute the diff between two file contents.

        Args:
            filename: Name of the file.
            original: Original content.
            modified: Modified content.

        Returns:
            FileDiff with hunks and statistics.
        """
        file_diff = FileDiff(
            filename=filename,
            original_content=original,
            modified_content=modified,
        )

        if original == modified:
            return file_diff

        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )

        hunks = self._parse_unified_diff(diff, filename)
        file_diff.hunks = hunks
        file_diff.changed = len(hunks) > 0
        file_diff.added_count = sum(len(h.added_lines) for h in hunks)
        file_diff.removed_count = sum(len(h.removed_lines) for h in hunks)

        return file_diff

    def _parse_unified_diff(self, diff_lines: list[str], filename: str) -> list[DiffHunk]:
        """Parse unified diff output into structured hunks.

        Args:
            diff_lines: Lines from unified_diff output.
            filename: Name of the file being diffed.

        Returns:
            List of DiffHunk objects.
        """
        hunks: list[DiffHunk] = []
        current_hunk: DiffHunk | None = None
        context_before: list[str] = []

        for line in diff_lines:
            if line.startswith("+++") or line.startswith("---"):
                continue
            elif line.startswith("@@"):
                if current_hunk is not None and context_before:
                    current_hunk.context_before = context_before[:-2] if len(context_before) > 2 else []
                # Parse line number from @@ -X,Y +A,B @@
                try:
                    parts = line.split()
                    if len(parts) >= 2:
                        orig_range = parts[1].lstrip("-").split(",")
                        current_hunk = DiffHunk(
                            filename=filename,
                            start_line=int(orig_range[0]),
                        )
                        hunks.append(current_hunk)
                except (ValueError, IndexError):
                    current_hunk = DiffHunk(filename=filename)
                context_before = []
            elif current_hunk is not None:
                if line.startswith("+"):
                    current_hunk.added_lines.append(line[1:].rstrip("\n"))
                    context_before = []
                elif line.startswith("-"):
                    current_hunk.removed_lines.append(line[1:].rstrip("\n"))
                    context_before = []
                else:
                    context_before.append(line[1:].rstrip("\n") if line.startswith(" ") else line.rstrip("\n"))

        # Attach trailing context to last hunk
        if current_hunk is not None and context_before:
            current_hunk.context_after = context_before[-2:] if len(context_before) > 2 else context_before

        return hunks

    def _get_files(self, directory: Path, patterns: list[str] | None = None) -> set:
        """Get all files in a directory, optionally filtered by patterns.

        Args:
            directory: Root directory to search.
            patterns: Glob patterns to filter files.

        Returns:
            Set of relative file paths.
        """
        files = set()
        if not directory.exists():
            return files

        for path in directory.rglob("*"):
            if path.is_file():
                rel = str(path.relative_to(directory))
                # Skip hidden directories and cache
                if rel.startswith(".git") or "__pycache__" in rel or ".pyc" in rel:
                    continue
                if patterns is None:
                    files.add(rel)
                else:
                    for pattern in patterns:
                        if path.match(pattern):
                            files.add(rel)
                            break

        return files

    def format_diff_markdown(self, workspace_diff: WorkspaceDiff) -> str:
        """Format a workspace diff as Markdown for display.

        Args:
            workspace_diff: The diff result to format.

        Returns:
            Markdown string showing the diff.
        """
        lines = []
        lines.append("## Workspace Changes")
        lines.append("")
        lines.append(f"- **Files changed:** {workspace_diff.files_changed}")
        lines.append(f"- **Lines added:** {workspace_diff.total_added}")
        lines.append(f"- **Lines removed:** {workspace_diff.total_removed}")
        lines.append("")

        for file_diff in workspace_diff.files:
            if not file_diff.changed:
                continue

            lines.append(f"### `{file_diff.filename}`")
            lines.append("")
            lines.append("```diff")

            for hunk in file_diff.hunks:
                for line in hunk.context_before[:3]:
                    lines.append(f" {line}")
                for line in hunk.removed_lines:
                    lines.append(f"-{line}")
                for line in hunk.added_lines:
                    lines.append(f"+{line}")
                for line in hunk.context_after[:3]:
                    lines.append(f" {line}")

            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def format_diff_text(self, workspace_diff: WorkspaceDiff) -> str:
        """Format a workspace diff as plain text for CLI display.

        Args:
            workspace_diff: The diff result to format.

        Returns:
            Plain text string showing the diff.
        """
        lines = []
        lines.append(
            f"Workspace changes: {workspace_diff.files_changed} files, "
            f"+{workspace_diff.total_added}/-{workspace_diff.total_removed} lines"
        )
        lines.append("")

        for file_diff in workspace_diff.files:
            if not file_diff.changed:
                continue

            lines.append(f"  {file_diff.filename} (+{file_diff.added_count}/-{file_diff.removed_count})")
            for hunk in file_diff.hunks[:3]:
                for line in hunk.removed_lines[:2]:
                    lines.append(f"    - {line}")
                for line in hunk.added_lines[:2]:
                    lines.append(f"    + {line}")

        return "\n".join(lines)
