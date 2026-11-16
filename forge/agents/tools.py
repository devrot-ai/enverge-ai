"""Agent tool definitions with schemas and path traversal prevention.

Defines the controlled tools available to agents during execution.
Each tool has a strict schema for argument validation and enforces
workspace boundaries to prevent path traversal attacks.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Tool Schema
# ---------------------------------------------------------------------------


@dataclass
class ToolParameter:
    """Schema for a single tool parameter."""

    name: str
    type: str  # "string", "integer", "boolean", "array"
    required: bool = True
    description: str = ""
    default: Any = None


@dataclass
class ToolDefinition:
    """Schema for an agent tool.

    Attributes:
        name: Unique tool identifier.
        description: Human-readable description for the agent.
        parameters: List of parameter schemas.
        handler: Callable that executes the tool.
    """

    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    handler: Callable | None = None


# ---------------------------------------------------------------------------
# Path Traversal Prevention
# ---------------------------------------------------------------------------


def validate_path(workspace: Path, requested_path: str) -> Path:
    """Validate that a requested path stays within the workspace.

    Args:
        workspace: The agent's workspace root.
        requested_path: The path requested by the agent.

    Returns:
        Resolved Path object within the workspace.

    Raises:
        ValueError: If the path attempts to escape the workspace.
    """
    if not requested_path:
        raise ValueError("Empty path provided")

    # Normalize the requested path
    try:
        requested = Path(requested_path)
    except Exception as e:
        raise ValueError(f"Invalid path format: {e}")

    # Resolve both paths to absolute
    workspace_resolved = workspace.resolve()

    # If the path is absolute, it must be within workspace
    if requested.is_absolute():
        requested_resolved = requested.resolve()
    else:
        requested_resolved = (workspace_resolved / requested).resolve()

    # Check the resolved path is within workspace
    try:
        requested_resolved.relative_to(workspace_resolved)
    except ValueError:
        raise ValueError(f"Path traversal detected: '{requested_path}' escapes workspace")

    return requested_resolved


def sanitize_file_content(content: str, max_length: int = 100_000) -> str:
    """Sanitize file content for safe display.

    Args:
        content: Raw file content.
        max_length: Maximum characters to return.

    Returns:
        Truncated content if too long.
    """
    if len(content) > max_length:
        return content[:max_length] + f"\n... [truncated, {len(content)} total chars]"
    return content


# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------


class ToolExecutor:
    """Executes agent tools with validation and sandboxing.

    Provides the actual implementation of each tool with proper
    error handling, path validation, and output sanitization.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def list_files(self, args: dict[str, Any]) -> str:
        """List files in the workspace or a subdirectory.

        Args:
            args: {"path": str, "recursive": bool}

        Returns:
            Formatted file listing.
        """
        target_path = self.workspace
        recursive = args.get("recursive", False)

        if "path" in args and args["path"]:
            target_path = validate_path(self.workspace, args["path"])

        if not target_path.exists():
            return f"Error: Path does not exist: {target_path}"

        if not target_path.is_dir():
            return f"Error: Not a directory: {target_path}"

        files = []
        if recursive:
            for item in sorted(target_path.rglob("*")):
                if item.is_file():
                    rel = item.relative_to(self.workspace)
                    files.append(str(rel))
        else:
            for item in sorted(target_path.iterdir()):
                rel = item.relative_to(self.workspace)
                if item.is_dir():
                    files.append(str(rel) + "/")
                else:
                    files.append(str(rel))

        if not files:
            return "No files found."

        return "\n".join(files)

    def read_file(self, args: dict[str, Any]) -> str:
        """Read the contents of a file.

        Args:
            args: {"path": str}

        Returns:
            File contents.
        """
        file_path = validate_path(self.workspace, args.get("path", ""))

        if not file_path.exists():
            return f"Error: File not found: {file_path}"

        if not file_path.is_file():
            return f"Error: Not a file: {file_path}"

        try:
            content = file_path.read_text(encoding="utf-8")
            return sanitize_file_content(content)
        except UnicodeDecodeError:
            return f"Error: Cannot read binary file: {file_path}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"

    def search_code(self, args: dict[str, Any]) -> str:
        """Search for text patterns in source files.

        Args:
            args: {"pattern": str, "path": str, "file_type": str}

        Returns:
            Matching lines with file paths and line numbers.
        """
        pattern = args.get("pattern", "")
        if not pattern:
            return "Error: Empty search pattern"

        search_dir = self.workspace
        if "path" in args and args["path"]:
            search_dir = validate_path(self.workspace, args["path"])

        file_type = args.get("file_type", "*.py")

        try:
            matches = []
            for file_path in search_dir.rglob(file_type):
                if file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        for i, line in enumerate(content.splitlines(), 1):
                            if re.search(pattern, line):
                                rel = file_path.relative_to(self.workspace)
                                matches.append(f"{rel}:{i}: {line.strip()}")
                    except (UnicodeDecodeError, PermissionError):
                        continue

            if not matches:
                return f"No matches found for pattern: {pattern}"

            return "\n".join(matches[:100])  # Limit output
        except Exception as e:
            return f"Error searching: {e}"

    def write_file(self, args: dict[str, Any]) -> str:
        """Write content to a file.

        Args:
            args: {"path": str, "content": str}

        Returns:
            Success or error message.
        """
        file_path = validate_path(self.workspace, args.get("path", ""))
        content = args.get("content", "")

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            file_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} characters to {file_path.relative_to(self.workspace)}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            return f"Error writing file: {e}"

    def run_public_tests(self, args: dict[str, Any]) -> str:
        """Run the public test suite.

        Args:
            args: {"test_path": str}

        Returns:
            Test output.
        """
        import subprocess

        test_path = args.get("test_path", "tests/test_public.py")
        test_full_path = validate_path(self.workspace, test_path)

        if not test_full_path.exists():
            return f"Error: Test file not found: {test_path}"

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_full_path), "-v", "--tb=short"],
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=60,
            )
            output = result.stdout
            if result.stderr:
                output += result.stderr
            return sanitize_file_content(output)
        except subprocess.TimeoutExpired:
            return "Error: Test execution timed out (60s limit)"
        except Exception as e:
            return f"Error running tests: {e}"

    def inspect_test_output(self, args: dict[str, Any]) -> str:
        """Inspect recent test output from a file.

        Args:
            args: {"output_file": str}

        Returns:
            Test output content.
        """
        output_file = args.get("output_file", "test_output.txt")
        file_path = validate_path(self.workspace, output_file)

        if not file_path.exists():
            return f"Error: Output file not found: {output_file}"

        try:
            content = file_path.read_text(encoding="utf-8")
            return sanitize_file_content(content)
        except Exception as e:
            return f"Error reading output: {e}"

    def inspect_git_diff(self, args: dict[str, Any]) -> str:
        """Show the git diff of changes made in the workspace.

        Args:
            args: {"file": str} (optional, show diff for specific file)

        Returns:
            Git diff output.
        """
        import subprocess

        try:
            cmd = ["git", "diff"]
            if "file" in args and args["file"]:
                cmd.append(args["file"])

            result = subprocess.run(
                cmd,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout
            if not output:
                return "No changes detected."
            return sanitize_file_content(output)
        except subprocess.TimeoutExpired:
            return "Error: Git diff timed out"
        except Exception as e:
            return f"Error running git diff: {e}"

    def finish_task(self, args: dict[str, Any]) -> str:
        """Signal that the agent has finished the task.

        Args:
            args: {"belief": str} (optional, agent's confidence statement)

        Returns:
            Confirmation message.
        """
        belief = args.get("belief", "Task completed")
        return f"Task finished. Agent belief: {belief}"


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------


def get_all_tools() -> dict[str, ToolDefinition]:
    """Return all available tool definitions.

    Returns:
        Dictionary mapping tool names to their definitions.
    """
    return {
        "list_files": ToolDefinition(
            name="list_files",
            description="List files in the workspace or a subdirectory",
            parameters=[
                ToolParameter("path", "string", required=False, default="", description="Subdirectory to list"),
                ToolParameter("recursive", "boolean", required=False, default=False, description="List recursively"),
            ],
        ),
        "read_file": ToolDefinition(
            name="read_file",
            description="Read the contents of a file",
            parameters=[
                ToolParameter("path", "string", required=True, description="Path to the file"),
            ],
        ),
        "search_code": ToolDefinition(
            name="search_code",
            description="Search for text patterns in source files",
            parameters=[
                ToolParameter("pattern", "string", required=True, description="Regex pattern to search for"),
                ToolParameter("path", "string", required=False, default="", description="Directory to search in"),
                ToolParameter("file_type", "string", required=False, default="*.py", description="File glob pattern"),
            ],
        ),
        "write_file": ToolDefinition(
            name="write_file",
            description="Write content to a file (creates if not exists)",
            parameters=[
                ToolParameter("path", "string", required=True, description="Path to the file"),
                ToolParameter("content", "string", required=True, description="File content"),
            ],
        ),
        "run_public_tests": ToolDefinition(
            name="run_public_tests",
            description="Run the public test suite",
            parameters=[
                ToolParameter(
                    "test_path",
                    "string",
                    required=False,
                    default="tests/test_public.py",
                    description="Path to test file",
                ),
            ],
        ),
        "inspect_test_output": ToolDefinition(
            name="inspect_test_output",
            description="Inspect recent test output from a file",
            parameters=[
                ToolParameter(
                    "output_file", "string", required=False, default="test_output.txt", description="Output file path"
                ),
            ],
        ),
        "inspect_git_diff": ToolDefinition(
            name="inspect_git_diff",
            description="Show the git diff of changes made in the workspace",
            parameters=[
                ToolParameter("file", "string", required=False, default="", description="Specific file to diff"),
            ],
        ),
        "finish_task": ToolDefinition(
            name="finish_task",
            description="Signal that the agent has finished the task",
            parameters=[
                ToolParameter(
                    "belief",
                    "string",
                    required=False,
                    default="Task completed",
                    description="Agent's confidence statement",
                ),
            ],
        ),
    }


def create_tool_executor(workspace: Path) -> ToolExecutor:
    """Create a ToolExecutor for a given workspace.

    Args:
        workspace: Path to the agent's workspace.

    Returns:
        Configured ToolExecutor instance.
    """
    return ToolExecutor(workspace)


def validate_tool_args(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Validate tool arguments against the tool's schema.

    Args:
        tool_name: Name of the tool.
        args: Arguments to validate.

    Returns:
        Validated arguments with defaults applied.

    Raises:
        ValueError: If required arguments are missing or types are wrong.
    """
    tools = get_all_tools()
    if tool_name not in tools:
        raise ValueError(f"Unknown tool: {tool_name}")

    tool_def = tools[tool_name]
    validated = {}

    # Check required parameters
    for param in tool_def.parameters:
        if param.required and param.name not in args:
            raise ValueError(f"Missing required parameter: {param.name} for tool {tool_name}")

    # Apply defaults and validate types
    for param in tool_def.parameters:
        value = args.get(param.name, param.default)
        if value is None and not param.required:
            validated[param.name] = param.default
            continue

        # Type checking
        if param.type == "string" and not isinstance(value, str):
            raise ValueError(f"Parameter {param.name} must be a string")
        elif param.type == "integer" and not isinstance(value, int):
            raise ValueError(f"Parameter {param.name} must be an integer")
        elif param.type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"Parameter {param.name} must be a boolean")

        validated[param.name] = value

    return validated
