"""Static analysis checks for agent workspaces.

Runs flake8 and mypy on agent workspace as additional verification criteria.
Optional — not all projects use type hints or follow flake8 rules.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StaticAnalysisResult:
    """Result of static analysis on a workspace.

    Attributes:
        passed: Whether static analysis passed (no errors).
        errors: Number of errors found.
        warnings: Number of warnings found.
        flake8_output: Raw flake8 output.
        mypy_output: Raw mypy output.
        details: Human-readable summary.
    """

    passed: bool = False
    errors: int = 0
    warnings: int = 0
    flake8_output: str = ""
    mypy_output: str = ""
    details: str = ""


class StaticAnalyzer:
    """Runs static analysis checks on agent workspaces.

    Uses flake8 for lint errors and mypy for type errors.
    Both tools are optional — if missing, the analyzer skips that check.
    """

    def __init__(
        self,
        run_flake8: bool = True,
        run_mypy: bool = True,
        ignore_warnings: bool = False,
    ):
        """Initialize the static analyzer.

        Args:
            run_flake8: Whether to run flake8 lint checks.
            run_mypy: Whether to run mypy type checks.
            ignore_warnings: Whether to treat warnings as non-fatal.
        """
        self.run_flake8 = run_flake8
        self.run_mypy = run_mypy
        self.ignore_warnings = ignore_warnings

    def check(self, workspace_dir: Path) -> StaticAnalysisResult:
        """Run static analysis on a workspace.

        Args:
            workspace_dir: Path to the agent's workspace.

        Returns:
            StaticAnalysisResult with pass/fail and details.
        """
        result = StaticAnalysisResult()
        issues: list[str] = []

        if self.run_flake8:
            flake8_result = self._run_flake8(workspace_dir)
            result.flake8_output = flake8_result["output"]
            result.errors += flake8_result["errors"]
            result.warnings += flake8_result["warnings"]
            if flake8_result["errors"] > 0:
                issues.append(f"flake8: {flake8_result['errors']} errors")
            if flake8_result["warnings"] > 0 and not self.ignore_warnings:
                issues.append(f"flake8: {flake8_result['warnings']} warnings")

        if self.run_mypy:
            mypy_result = self._run_mypy(workspace_dir)
            result.mypy_output = mypy_result["output"]
            result.errors += mypy_result["errors"]
            result.warnings += mypy_result["warnings"]
            if mypy_result["errors"] > 0:
                issues.append(f"mypy: {mypy_result['errors']} errors")
            if mypy_result["warnings"] > 0 and not self.ignore_warnings:
                issues.append(f"mypy: {mypy_result['warnings']} warnings")

        result.passed = result.errors == 0
        if issues:
            result.details = "; ".join(issues)
        else:
            result.details = "Static analysis passed"

        return result

    def _run_flake8(self, workspace_dir: Path) -> dict:
        """Run flake8 on the workspace.

        Args:
            workspace_dir: Path to the workspace.

        Returns:
            Dict with output, errors, and warnings counts.
        """
        try:
            result = subprocess.run(
                ["flake8", str(workspace_dir), "--count", "--select=E,F,W"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
            errors = output.count("E")
            warnings = output.count("W")
            return {"output": output, "errors": errors, "warnings": warnings}
        except FileNotFoundError:
            return {"output": "flake8 not installed", "errors": 0, "warnings": 0}
        except subprocess.TimeoutExpired:
            return {"output": "flake8 timed out", "errors": 0, "warnings": 0}

    def _run_mypy(self, workspace_dir: Path) -> dict:
        """Run mypy on the workspace.

        Args:
            workspace_dir: Path to the workspace.

        Returns:
            Dict with output, errors, and warnings counts.
        """
        try:
            result = subprocess.run(
                ["mypy", str(workspace_dir), "--ignore-missing-imports"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
            errors = output.count("Error")
            warnings = output.count("Warning")
            return {"output": output, "errors": errors, "warnings": warnings}
        except FileNotFoundError:
            return {"output": "mypy not installed", "errors": 0, "warnings": 0}
        except subprocess.TimeoutExpired:
            return {"output": "mypy timed out", "errors": 0, "warnings": 0}
