"""Independent verifier: evaluates agent output in isolation.

Runs hidden tests and regression checks against the agent's workspace.
Never exposes hidden test content to the agent.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from forge.core.schemas import VerificationResult, WorldSpec


class Verifier:
    """Independently verifies agent output.

    Runs hidden tests and regression checks in a controlled manner.
    """

    def verify(
        self,
        workspace_dir: Path,
        world_spec: WorldSpec,
    ) -> VerificationResult:
        """Verify an agent's workspace against hidden tests.

        Args:
            workspace_dir: Path to the agent's modified workspace.
            world_spec: The world specification.

        Returns:
            VerificationResult with pass/fail details.
        """
        test_results: dict[str, bool] = {}

        # Run public tests (regression check)
        existing_passed = self._run_public_tests(workspace_dir, test_results)

        # Run hidden tests
        hidden_passed = self._run_hidden_tests(workspace_dir, test_results)

        # Determine overall pass
        passed = existing_passed and hidden_passed

        # Compute score
        total = len(test_results)
        passed_count = sum(1 for v in test_results.values() if v)
        score = passed_count / total if total > 0 else 0.0

        details = []
        if not existing_passed:
            details.append("Existing tests failed - regression detected")
        if not hidden_passed:
            details.append("Hidden tests failed - bug not fixed")
        if passed:
            details.append("All tests passed - task completed successfully")

        return VerificationResult(
            run_id="",  # Set by caller
            passed=passed,
            test_results=test_results,
            existing_tests_passed=existing_passed,
            hidden_tests_passed=hidden_passed,
            regression_tests_passed=existing_passed,
            score=score,
            details="; ".join(details) if details else "Verification complete",
        )

    def _run_public_tests(self, workspace_dir: Path, test_results: dict[str, bool]) -> bool:
        """Run public tests for regression checking.

        Args:
            workspace_dir: Path to the workspace.
            test_results: Dict to populate with results.

        Returns:
            True if all public tests pass.
        """
        test_file = workspace_dir / "tests" / "test_public.py"
        if not test_file.exists():
            return True  # No public tests to run

        result = subprocess.run(
            ["python", "-m", "pytest", str(test_file), "-v", "--tb=short", "-q"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Parse output for individual test results
        output = result.stdout + result.stderr
        for line in output.split("\n"):
            if "PASSED" in line:
                test_name = line.strip().split()[0] if line.strip() else "unknown"
                test_results[test_name] = True
            elif "FAILED" in line:
                test_name = line.strip().split()[0] if line.strip() else "unknown"
                test_results[test_name] = False

        return result.returncode == 0

    def _run_hidden_tests(self, workspace_dir: Path, test_results: dict[str, bool]) -> bool:
        """Run hidden tests for acceptance checking.

        Args:
            workspace_dir: Path to the workspace.
            test_results: Dict to populate with results.

        Returns:
            True if all hidden tests pass.
        """
        hidden_dir = workspace_dir / ".hidden_tests"
        if not hidden_dir.exists():
            return False  # No hidden tests found

        test_file = hidden_dir / "test_hidden.py"
        if not test_file.exists():
            return False

        result = subprocess.run(
            ["python", "-m", "pytest", str(test_file), "-v", "--tb=short", "-q"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Parse output for individual test results
        output = result.stdout + result.stderr
        for line in output.split("\n"):
            if "PASSED" in line:
                test_name = line.strip().split()[0] if line.strip() else "unknown"
                test_results[test_name] = True
            elif "FAILED" in line:
                test_name = line.strip().split()[0] if line.strip() else "unknown"
                test_results[test_name] = False

        return result.returncode == 0
