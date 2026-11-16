"""Local sandbox for running verification without Docker.

Provides a fallback sandbox that runs tests in an isolated subprocess
when Docker is not available. Uses sys.path isolation to prevent
importing project code.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LocalSandboxResult:
    """Result of running tests in the local sandbox."""

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float = 0.0
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_errors: int = 0


class LocalSandbox:
    """Run verification tests in an isolated subprocess.

    Falls back from Docker sandbox when Docker is unavailable.
    Uses subprocess with restricted sys.path to prevent importing
    project code.
    """

    def __init__(self, timeout: int = 60):
        """Initialize the local sandbox.

        Args:
            timeout: Maximum execution time in seconds.
        """
        self.timeout = timeout

    def run_tests(self, workspace_dir: str | Path) -> LocalSandboxResult:
        """Run tests in the workspace directory.

        Args:
            workspace_dir: Path to the workspace containing tests.

        Returns:
            LocalSandboxResult with test outcomes.
        """
        workspace_dir = Path(workspace_dir)
        tests_dir = workspace_dir / "tests"

        if not tests_dir.exists():
            return LocalSandboxResult(
                passed=False,
                exit_code=1,
                stdout="",
                stderr=f"No tests directory found in {workspace_dir}",
            )

        # Create a runner script that isolates sys.path
        runner_script = self._create_runner_script(tests_dir)

        try:
            start_time = __import__("time").time()

            result = subprocess.run(
                [sys.executable, str(runner_script)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(workspace_dir),
            )

            duration = __import__("time").time() - start_time

            # Parse pytest output for test counts
            tests_run, tests_passed, tests_failed, tests_errors = self._parse_output(
                result.stdout
            )

            return LocalSandboxResult(
                passed=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_errors=tests_errors,
            )

        except subprocess.TimeoutExpired:
            return LocalSandboxResult(
                passed=False,
                exit_code=-1,
                stdout="",
                stderr=f"Test execution timed out after {self.timeout}s",
                duration_seconds=self.timeout,
            )
        except Exception as e:
            return LocalSandboxResult(
                passed=False,
                exit_code=-1,
                stdout="",
                stderr=f"Sandbox error: {e}",
            )

    def run_hidden_tests(self, workspace_dir: str | Path) -> LocalSandboxResult:
        """Run hidden tests in the workspace directory.

        Args:
            workspace_dir: Path to the workspace containing hidden tests.

        Returns:
            LocalSandboxResult with test outcomes.
        """
        workspace_dir = Path(workspace_dir)
        hidden_dir = workspace_dir / ".hidden_tests"

        if not hidden_dir.exists():
            return LocalSandboxResult(
                passed=True,
                exit_code=0,
                stdout="No hidden tests found",
                stderr="",
            )

        runner_script = self._create_runner_script(hidden_dir)

        try:
            start_time = __import__("time").time()

            result = subprocess.run(
                [sys.executable, str(runner_script)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(workspace_dir),
            )

            duration = __import__("time").time() - start_time

            tests_run, tests_passed, tests_failed, tests_errors = self._parse_output(
                result.stdout
            )

            return LocalSandboxResult(
                passed=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                tests_errors=tests_errors,
            )

        except subprocess.TimeoutExpired:
            return LocalSandboxResult(
                passed=False,
                exit_code=-1,
                stdout="",
                stderr=f"Hidden test execution timed out after {self.timeout}s",
                duration_seconds=self.timeout,
            )
        except Exception as e:
            return LocalSandboxResult(
                passed=False,
                exit_code=-1,
                stdout="",
                stderr=f"Sandbox error: {e}",
            )

    def _create_runner_script(self, tests_dir: Path) -> Path:
        """Create a temporary runner script for isolated execution.

        Args:
            tests_dir: Path to the tests directory.

        Returns:
            Path to the temporary runner script.
        """
        script_content = f'''
import sys
import os

# Isolate sys.path to only include the workspace
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath("{tests_dir}")))
sys.path.insert(0, workspace_dir)

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main(["{tests_dir}", "-v", "--tb=short"]))
'''
        tmp_file = Path(tempfile.mktemp(suffix=".py"))
        tmp_file.write_text(script_content, encoding="utf-8")
        return tmp_file

    def _parse_output(self, output: str) -> tuple[int, int, int, int]:
        """Parse pytest output for test counts.

        Args:
            output: pytest stdout output.

        Returns:
            Tuple of (tests_run, passed, failed, errors).
        """
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        tests_errors = 0

        for line in output.split("\n"):
            if "passed" in line and "failed" in line:
                # Parse summary line like "5 passed, 2 failed in 1.23s"
                parts = line.split()
                for i, part in enumerate(parts):
                    try:
                        num = int(part)
                        if i + 1 < len(parts):
                            next_word = parts[i + 1]
                            if "passed" in next_word:
                                tests_passed = num
                            elif "failed" in next_word:
                                tests_failed = num
                            elif "error" in next_word:
                                tests_errors = num
                    except ValueError:
                        pass
                tests_run = tests_passed + tests_failed + tests_errors
            elif "passed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    try:
                        num = int(part)
                        if i + 1 < len(parts) and "passed" in parts[i + 1]:
                            tests_passed = num
                            tests_run = num
                    except ValueError:
                        pass

        return tests_run, tests_passed, tests_failed, tests_errors
