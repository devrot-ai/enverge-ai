"""Validators: independent verification of worlds, tasks, and verifiers.

Before any task is released to an agent, ForgeLab independently validates it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from forge.core.schemas import TaskSpec, ValidationStatus, WorldSpec
from forge.world_factory.seeder import get_mutation, revert_mutation


class WorldValidator:
    """Validates generated worlds for correctness."""

    def validate(self, world_spec: WorldSpec) -> tuple[ValidationStatus, list[str]]:
        """Validate a generated world.

        Checks:
        - Repository exists
        - Required files exist
        - The intentional defect is present
        - Environment can be reset

        Args:
            world_spec: The world to validate.

        Returns:
            Tuple of (status, list of issues).
        """
        issues = []
        world_dir = Path(world_spec.metadata.get("world_dir", ""))

        if not world_dir.exists():
            return ValidationStatus.INVALID, ["World directory does not exist"]

        # Check required files
        if not (world_dir / "app.py").exists():
            issues.append("app.py not found")

        if not (world_dir / "tests" / "test_public.py").exists():
            issues.append("Public tests not found")

        if not (world_dir / ".hidden_tests" / "test_hidden.py").exists():
            issues.append("Hidden tests not found")

        # Check mutation is applied
        if world_spec.mutation_id:
            app_content = (world_dir / "app.py").read_text()
            mutation = get_mutation(world_spec.mutation_id)
            if mutation:
                if mutation["replace_with"] not in app_content:
                    issues.append(f"Mutation '{world_spec.mutation_id}' not applied")

        if issues:
            return ValidationStatus.INVALID, issues
        return ValidationStatus.VALID, []


class TaskValidator:
    """Validates task specifications for feasibility."""

    def validate(self, task_spec: TaskSpec, world_spec: WorldSpec) -> tuple[ValidationStatus, list[str]]:
        """Validate a task specification.

        Checks:
        - Description matches the actual defect
        - Acceptance criteria are achievable
        - Constraints are consistent
        - Required files exist

        Args:
            task_spec: The task to validate.
            world_spec: The world the task operates on.

        Returns:
            Tuple of (status, list of issues).
        """
        issues = []

        # Check task has required fields
        if not task_spec.description:
            issues.append("Task description is empty")

        if not task_spec.world_id:
            issues.append("Task world_id is empty")

        if task_spec.world_id != world_spec.world_id:
            issues.append("Task world_id does not match world spec")

        # Check difficulty is reasonable
        if task_spec.difficulty_level < 1 or task_spec.difficulty_level > 5:
            issues.append(f"Difficulty level {task_spec.difficulty_level} out of range")

        # Check capabilities are specified
        if not task_spec.capabilities:
            issues.append("No capabilities specified")

        if issues:
            return ValidationStatus.INVALID, issues
        return ValidationStatus.VALID, []


class VerifierValidator:
    """Validates that the verifier itself works correctly.

    Tests the verifier against known-correct and known-incorrect states.
    """

    def validate(self, world_spec: WorldSpec) -> tuple[ValidationStatus, list[str]]:
        """Validate the verifier for a world.

        Checks:
        - Hidden tests fail on the broken code (negative test)
        - Hidden tests pass on the fixed code (positive test)

        Args:
            world_spec: The world to validate.

        Returns:
            Tuple of (status, list of issues).
        """
        issues = []
        world_dir = Path(world_spec.metadata.get("world_dir", ""))

        if not world_dir.exists():
            return ValidationStatus.INVALID, ["World directory does not exist"]

        # Check hidden tests fail on broken code (negative test)
        hidden_tests_dir = world_dir / ".hidden_tests"
        if not hidden_tests_dir.exists():
            issues.append("Hidden tests directory not found")
            return ValidationStatus.INVALID, issues

        # Run hidden tests on broken code
        result = self._run_tests(world_dir, hidden_tests_dir)
        if result.returncode == 0:
            issues.append("Hidden tests pass on broken code - verifier may be defective")

        # Apply reference fix and check tests pass (positive test)
        if world_spec.mutation_id:
            try:
                revert_mutation(world_dir, world_spec.mutation_id)
                result = self._run_tests(world_dir, hidden_tests_dir)
                if result.returncode != 0:
                    issues.append("Hidden tests fail on fixed code - verifier may be defective")
                # Re-apply mutation to restore broken state
                from forge.world_factory.seeder import apply_mutation

                apply_mutation(world_dir, world_spec.mutation_id)
            except Exception as e:
                issues.append(f"Could not apply reference fix: {e}")

        if issues:
            return ValidationStatus.INVALID, issues
        return ValidationStatus.VALID, []

    def _run_tests(self, world_dir: Path, tests_dir: Path) -> subprocess.CompletedProcess:
        """Run pytest on a test directory."""
        return subprocess.run(
            ["python", "-m", "pytest", str(tests_dir), "-v", "--tb=short"],
            cwd=world_dir,
            capture_output=True,
            timeout=30,
        )


class ReferenceValidator:
    """Validates that the reference solution actually fixes the bug."""

    def validate(self, world_spec: WorldSpec) -> tuple[ValidationStatus, list[str]]:
        """Validate the reference solution.

        Applies the reference fix and runs all tests.

        Args:
            world_spec: The world to validate.

        Returns:
            Tuple of (status, list of issues).
        """
        issues = []
        world_dir = Path(world_spec.metadata.get("world_dir", ""))

        if not world_dir.exists():
            return ValidationStatus.INVALID, ["World directory does not exist"]

        if not world_spec.mutation_id:
            return ValidationStatus.INVALID, ["No mutation ID to validate"]

        # Apply reference fix
        try:
            revert_mutation(world_dir, world_spec.mutation_id)
        except Exception as e:
            return ValidationStatus.INVALID, [f"Could not apply reference fix: {e}"]

        # Run public tests
        public_tests = world_dir / "tests" / "test_public.py"
        if public_tests.exists():
            result = self._run_tests(world_dir, str(public_tests))
            if result.returncode != 0:
                issues.append("Reference fix breaks public tests")

        # Run hidden tests
        hidden_tests = world_dir / ".hidden_tests" / "test_hidden.py"
        if hidden_tests.exists():
            result = self._run_tests(world_dir, str(hidden_tests))
            if result.returncode != 0:
                issues.append("Reference fix does not pass hidden tests")

        # Re-apply mutation to restore broken state
        try:
            from forge.world_factory.seeder import apply_mutation

            apply_mutation(world_dir, world_spec.mutation_id)
        except Exception as e:
            issues.append(f"Could not restore mutation: {e}")

        if issues:
            return ValidationStatus.INVALID, issues
        return ValidationStatus.VALID, []

    def _run_tests(self, world_dir: Path, test_path: str) -> subprocess.CompletedProcess:
        """Run pytest on a test file."""
        return subprocess.run(
            ["python", "-m", "pytest", test_path, "-v", "--tb=short"],
            cwd=world_dir,
            capture_output=True,
            timeout=30,
        )
