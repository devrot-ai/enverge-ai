"""Error injection for adversarial testing.

Injects runtime errors into agent workspace code to test robustness.
Used to verify that agent fixes work under adversarial conditions.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ErrorInjectionResult:
    """Result of injecting an error into the workspace."""

    error_type: str
    injected: bool = False
    agent_handled: bool = False
    details: str = ""
    file_path: str = ""
    line_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "error_type": self.error_type,
            "injected": self.injected,
            "agent_handled": self.agent_handled,
            "details": self.details,
            "file_path": self.file_path,
            "line_number": self.line_number,
        }


class ErrorInjector:
    """Inject runtime errors into workspace code to test agent robustness.

    Error types:
    - syntax_error: Invalid syntax (missing colon, unclosed parenthesis)
    - import_error: Missing module import
    - type_error: Wrong argument types
    - attribute_error: Missing attribute access
    - runtime_error: Division by zero, index out of bounds

    Each injection modifies a random Python file in the workspace.
    """

    # Error injection patterns
    SYNTAX_ERROR_INJECTIONS = [
        # Missing colon in function definition
        (r"def (\w+)\(([^)]*)\)", r"def \1(\2)"),  # removes colon
        # Unclosed parenthesis
        (r"return (\w+)", r"return (\1"),
    ]

    IMPORT_ERROR_INJECTIONS = [
        "import nonexistent_module_xyz_123\n",
        "from fake_library import FakeClass\n",
    ]

    TYPE_ERROR_INJECTIONS = [
        '    _type_check = "string" + 123  # type check\n',
        '    _type_check = int("not_a_number")  # type check\n',
    ]

    ATTRIBUTE_ERROR_INJECTIONS = [
        '    _attr_check = nonexistent_variable_xyz.attr  # attr check\n',
        '    _attr_check = None.nonexistent_method()  # attr check\n',
    ]

    RUNTIME_ERROR_INJECTIONS = [
        '    _runtime_check = 1 / 0  # runtime check\n',
        '    _runtime_check = [1, 2, 3][999]  # runtime check\n',
    ]

    ERROR_TYPE_MAP = {
        "syntax_error": "syntax_error",
        "import_error": "import_error",
        "type_error": "type_error",
        "attribute_error": "attribute_error",
        "runtime_error": "runtime_error",
    }

    def __init__(self):
        """Initialize the error injector."""
        pass

    def inject(
        self,
        workspace_dir: str | Path,
        error_type: str,
    ) -> ErrorInjectionResult:
        """Inject an error into the workspace.

        Args:
            workspace_dir: Path to the agent's workspace.
            error_type: Type of error to inject.

        Returns:
            ErrorInjectionResult with injection details.
        """
        workspace_dir = Path(workspace_dir)
        if error_type not in self.ERROR_TYPE_MAP:
            return ErrorInjectionResult(
                error_type=error_type,
                injected=False,
                details=f"Unknown error type: {error_type}",
            )

        # Find Python files in workspace
        py_files = list(workspace_dir.glob("*.py"))
        py_files.extend(workspace_dir.glob("**/*.py"))
        py_files = list(set(py_files))  # deduplicate

        if not py_files:
            return ErrorInjectionResult(
                error_type=error_type,
                injected=False,
                details="No Python files found in workspace",
            )

        # Pick a random file
        target_file = random.choice(py_files)

        try:
            content = target_file.read_text(encoding="utf-8")
            new_content, line_num = self._inject_error(content, error_type)

            if new_content is None:
                return ErrorInjectionResult(
                    error_type=error_type,
                    injected=False,
                    details=f"Could not inject error into {target_file.name}",
                )

            target_file.write_text(new_content, encoding="utf-8")

            return ErrorInjectionResult(
                error_type=error_type,
                injected=True,
                details=f"Injected {error_type} into {target_file.name}",
                file_path=str(target_file),
                line_number=line_num,
            )
        except Exception as e:
            return ErrorInjectionResult(
                error_type=error_type,
                injected=False,
                details=f"Error during injection: {e}",
                file_path=str(target_file),
            )

    def _inject_error(
        self,
        content: str,
        error_type: str,
    ) -> tuple[str | None, int]:
        """Inject a specific error type into code content.

        Args:
            content: Python source code.
            error_type: Type of error to inject.

        Returns:
            Tuple of (modified_content, line_number) or (None, 0) on failure.
        """
        lines = content.split("\n")

        if error_type == "syntax_error":
            return self._inject_syntax_error(lines)
        elif error_type == "import_error":
            return self._inject_import_error(lines)
        elif error_type == "type_error":
            return self._inject_type_error(lines)
        elif error_type == "attribute_error":
            return self._inject_attribute_error(lines)
        elif error_type == "runtime_error":
            return self._inject_runtime_error(lines)
        else:
            return None, 0

    def _inject_syntax_error(self, lines: list[str]) -> tuple[str | None, int]:
        """Inject a syntax error by removing a colon from a function definition."""
        for i, line in enumerate(lines):
            if re.match(r"\s*def \w+\([^)]*\):", line):
                lines[i] = line.rstrip(":")
                return "\n".join(lines), i + 1
        return None, 0

    def _inject_import_error(self, lines: list[str]) -> tuple[str | None, int]:
        """Inject a missing import at the top of the file."""
        injection = random.choice(self.IMPORT_ERROR_INJECTIONS)
        lines.insert(0, injection.strip())
        return "\n".join(lines), 1

    def _inject_type_error(self, lines: list[str]) -> tuple[str | None, int]:
        """Inject a type error inside a function body."""
        for i, line in enumerate(lines):
            if re.match(r"\s*def \w+", line):
                # Find the end of the function and inject before return
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("return "):
                        injection = random.choice(self.TYPE_ERROR_INJECTIONS)
                        lines.insert(j, injection)
                        return "\n".join(lines), j + 1
                    elif re.match(r"\s*def \w+", lines[j]) and j > i:
                        break
        # Fallback: inject at end
        injection = random.choice(self.TYPE_ERROR_INJECTIONS)
        lines.append(injection)
        return "\n".join(lines), len(lines)

    def _inject_attribute_error(self, lines: list[str]) -> tuple[str | None, int]:
        """Inject an attribute error inside a function body."""
        for i, line in enumerate(lines):
            if re.match(r"\s*def \w+", line):
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("return "):
                        injection = random.choice(self.ATTRIBUTE_ERROR_INJECTIONS)
                        lines.insert(j, injection)
                        return "\n".join(lines), j + 1
                    elif re.match(r"\s*def \w+", lines[j]) and j > i:
                        break
        injection = random.choice(self.ATTRIBUTE_ERROR_INJECTIONS)
        lines.append(injection)
        return "\n".join(lines), len(lines)

    def _inject_runtime_error(self, lines: list[str]) -> tuple[str | None, int]:
        """Inject a runtime error inside a function body."""
        for i, line in enumerate(lines):
            if re.match(r"\s*def \w+", line):
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith("return "):
                        injection = random.choice(self.RUNTIME_ERROR_INJECTIONS)
                        lines.insert(j, injection)
                        return "\n".join(lines), j + 1
                    elif re.match(r"\s*def \w+", lines[j]) and j > i:
                        break
        injection = random.choice(self.RUNTIME_ERROR_INJECTIONS)
        lines.append(injection)
        return "\n".join(lines), len(lines)

    def inject_multiple(
        self,
        workspace_dir: str | Path,
        error_types: list[str] | None = None,
        count: int = 3,
    ) -> list[ErrorInjectionResult]:
        """Inject multiple errors of different types.

        Args:
            workspace_dir: Path to the workspace.
            error_types: List of error types to inject. If None, random selection.
            count: Number of errors to inject.

        Returns:
            List of injection results.
        """
        if error_types is None:
            all_types = list(self.ERROR_TYPE_MAP.keys())
            error_types = random.sample(all_types, min(count, len(all_types)))

        results = []
        for error_type in error_types[:count]:
            result = self.inject(workspace_dir, error_type)
            results.append(result)

        return results
