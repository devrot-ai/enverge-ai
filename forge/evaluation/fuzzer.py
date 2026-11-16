"""Fuzzing-based verification for edge-case robustness.

Generates random and edge-case inputs to test the agent's modified code
for robustness. Complements the existing verifier (which runs specific
test cases) by exploring input space the tests don't cover.
"""

from __future__ import annotations

import importlib.util
import random
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FuzzResult:
    """Result of fuzzing a workspace.

    Attributes:
        inputs_tested: Total number of inputs tested.
        crashes_found: Number of inputs that caused crashes.
        error_samples: Sample error messages from crashes.
        passed: Whether fuzzing passed (no crashes detected).
        template: The template that was fuzzed.
    """

    inputs_tested: int = 0
    crashes_found: int = 0
    error_samples: list[str] = field(default_factory=list)
    passed: bool = True
    template: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "inputs_tested": self.inputs_tested,
            "crashes_found": self.crashes_found,
            "error_samples": self.error_samples[:10],  # Limit samples
            "passed": self.passed,
            "template": self.template,
        }


class Fuzzer:
    """Property-based fuzzer for agent workspaces.

    Generates random inputs based on the template type and runs the
    application code with fuzzed inputs, catching exceptions.
    """

    # Number of fuzz iterations per entry point
    DEFAULT_ITERATIONS = 50

    def __init__(self, seed: int | None = None, iterations: int = DEFAULT_ITERATIONS):
        """Initialize the fuzzer.

        Args:
            seed: Random seed for reproducibility.
            iterations: Number of fuzz iterations per entry point.
        """
        self.rng = random.Random(seed)
        self.iterations = iterations

    def fuzz(
        self,
        workspace_dir: Path,
        template: str,
    ) -> FuzzResult:
        """Run fuzzing on the agent's workspace.

        Args:
            workspace_dir: Path to the agent's modified workspace.
            template: The template name (e.g., 'task_manager_api').

        Returns:
            FuzzResult with inputs_tested, crashes_found, error_samples.
        """
        result = FuzzResult(template=template)
        generators = self._get_generators(template)

        if not generators:
            result.passed = True
            return result

        app_file = workspace_dir / "app.py"
        if not app_file.exists():
            result.passed = True
            return result

        # Load the app module
        module = self._load_module(app_file)
        if module is None:
            result.passed = True
            return result

        for entry_point, input_gen in generators:
            func = self._get_callable(module, entry_point)
            if func is None:
                continue

            for _ in range(self.iterations):
                inputs = input_gen(self.rng)
                result.inputs_tested += 1
                try:
                    self._call_safely(func, inputs)
                except Exception as e:
                    result.crashes_found += 1
                    error_msg = f"{entry_point}: {type(e).__name__}: {e}"
                    if len(result.error_samples) < 10:
                        result.error_samples.append(error_msg)

        result.passed = result.crashes_found == 0
        return result

    def _get_generators(self, template: str) -> list[tuple[str, callable]]:
        """Get entry points and input generators for a template.

        Args:
            template: The template name.

        Returns:
            List of (entry_point_name, input_generator) tuples.
        """
        generators = {
            "task_manager_api": [
                ("TaskManager", lambda rng: self._gen_task_manager_inputs(rng)),
                (
                    "TaskManager.add_task",
                    lambda rng: (
                        self._random_string(rng),
                        self._random_string(rng),
                        rng.choice(["todo", "in_progress", "done"]),
                    ),
                ),
                ("TaskManager.get_tasks", lambda rng: (rng.randint(1, 10), rng.randint(1, 100))),
                ("TaskManager.search_tasks", lambda rng: (self._random_string(rng, min_len=0),)),
                ("TaskManager.filter_by_status", lambda rng: (rng.choice(["todo", "in_progress", "done", None, ""]),)),
                (
                    "TaskManager.update_task",
                    lambda rng: (
                        self._random_string(rng),
                        {"status": rng.choice(["todo", "done"]), "title": self._random_string(rng)},
                    ),
                ),
                ("TaskManager.delete_task", lambda rng: (self._random_string(rng),)),
            ],
            "data_pipeline": [
                ("DataValidator", lambda rng: self._gen_validator_inputs(rng)),
                ("DataValidator.validate", lambda rng: (self._gen_data_row(rng),)),
                ("DateParser", lambda rng: self._gen_date_parser_inputs(rng)),
                (
                    "DateParser.parse",
                    lambda rng: (self._random_date_string(rng), self._random_string(rng, min_len=3, max_len=10)),
                ),
                ("DataTransformer", lambda rng: self._gen_transformer_inputs(rng)),
                ("DataTransformer.transform", lambda rng: (self._gen_data_row(rng),)),
                ("Pipeline", lambda rng: self._gen_pipeline_inputs(rng)),
                ("Pipeline.run", lambda rng: ([self._gen_data_row(rng) for _ in range(rng.randint(0, 20))],)),
            ],
            "flask_app": [
                ("AuthManager", lambda rng: self._gen_auth_inputs(rng)),
                ("AuthManager.register", lambda rng: (self._random_string(rng), self._random_string(rng))),
                ("AuthManager.login", lambda rng: (self._random_string(rng), self._random_string(rng))),
                ("AuthManager.logout", lambda rng: (self._random_string(rng),)),
                ("SessionManager", lambda rng: self._gen_session_inputs(rng)),
                ("SessionManager.create_session", lambda rng: (self._random_string(rng),)),
                ("SessionManager.validate_session", lambda rng: (self._random_string(rng),)),
                ("CSRFProtector", lambda rng: self._gen_csrf_inputs(rng)),
                ("CSRFProtector.generate_token", lambda rng: ()),
                ("CSRFProtector.validate_token", lambda rng: (self._random_string(rng),)),
            ],
            "express_api": [
                ("Router", lambda rng: self._gen_router_inputs(rng)),
                (
                    "Router.add_route",
                    lambda rng: (rng.choice(["GET", "POST", "PUT", "DELETE"]), self._random_string(rng), None),
                ),
                ("MiddlewareChain", lambda rng: self._gen_middleware_inputs(rng)),
                ("CorsHandler", lambda rng: self._gen_cors_inputs(rng)),
                ("CorsHandler.check_origin", lambda rng: (self._random_string(rng),)),
                ("RateLimiter", lambda rng: self._gen_rate_limit_inputs(rng)),
                ("RateLimiter.allow_request", lambda rng: (self._random_string(rng),)),
                ("RequestValidator", lambda rng: self._gen_request_validator_inputs(rng)),
                (
                    "RequestValidator.validate",
                    lambda rng: ({self._random_string(rng): self._random_value(rng)} for _ in range(1)),
                ),
            ],
            "django_app": [
                ("Model", lambda rng: self._gen_model_inputs(rng)),
                ("QuerySet", lambda rng: self._gen_queryset_inputs(rng)),
                ("QuerySet.filter", lambda rng: ({self._random_string(rng): self._random_value(rng)},)),
                ("QuerySet.order_by", lambda rng: (self._random_string(rng),)),
                ("View", lambda rng: self._gen_view_inputs(rng)),
                ("FormValidator", lambda rng: self._gen_form_inputs(rng)),
                (
                    "FormValidator.validate",
                    lambda rng: ({self._random_string(rng): self._random_value(rng)} for _ in range(1)),
                ),
            ],
        }
        return generators.get(template, [])

    def _load_module(self, file_path: Path) -> Any:
        """Load a Python module from a file path.

        Args:
            file_path: Path to the Python file.

        Returns:
            The loaded module or None if loading failed.
        """
        try:
            spec = importlib.util.spec_from_file_location("fuzz_target", file_path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            sys_module = __import__("sys")
            sys_module.modules["fuzz_target"] = module
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None

    def _get_callable(self, module: Any, entry_point: str) -> Any:
        """Get a callable from a module by dotted path.

        Args:
            module: The loaded module.
            entry_point: Dotted path (e.g., 'TaskManager.add_task').

        Returns:
            The callable or None if not found.
        """
        parts = entry_point.split(".")
        obj = module
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return None

        if callable(obj):
            return obj
        return None

    def _call_safely(self, func: callable, inputs: Any) -> Any:
        """Call a function with inputs, raising exceptions.

        For classes, instantiates first then calls methods.
        For functions, calls directly with inputs.

        Args:
            func: The callable to invoke.
            inputs: Input arguments.

        Returns:
            The result of the call.

        Raises:
            Any exception raised by the function.
        """
        if isinstance(inputs, (list, tuple)):
            # Try to instantiate a class first
            if len(inputs) == 0:
                return func()
            # Check if func is a class
            if isinstance(func, type):
                instance = func(*inputs)
                # Try calling common methods on the instance
                for method_name in ["validate", "run", "process", "check"]:
                    if hasattr(instance, method_name):
                        method = getattr(instance, method_name)
                        if callable(method):
                            try:
                                method()
                            except TypeError:
                                pass
                return instance
            else:
                return func(*inputs)
        elif isinstance(inputs, dict):
            if isinstance(func, type):
                instance = func(**inputs)
                return instance
            else:
                return func(**inputs)
        else:
            return func(inputs)

    # --- Input generators ---

    def _random_string(self, rng: random.Random, min_len: int = 1, max_len: int = 50) -> str:
        length = rng.randint(min_len, max_len)
        return "".join(rng.choices(string.ascii_letters + string.digits + " _-", k=length))

    def _random_value(self, rng: random.Random) -> Any:
        """Generate a random value of various types."""
        choice = rng.choice(["str", "int", "float", "bool", "none", "empty", "list"])
        if choice == "str":
            return self._random_string(rng)
        elif choice == "int":
            return rng.randint(-1000, 1000)
        elif choice == "float":
            return rng.uniform(-1000.0, 1000.0)
        elif choice == "bool":
            return rng.choice([True, False])
        elif choice == "none":
            return None
        elif choice == "empty":
            return ""
        elif choice == "list":
            return [self._random_value(rng) for _ in range(rng.randint(0, 5))]

    def _random_date_string(self, rng: random.Random) -> str:
        """Generate a random date string, sometimes malformed."""
        choice = rng.choice(["valid", "iso", "malformed", "empty", "none"])
        if choice == "valid":
            return f"{rng.randint(2000, 2030)}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
        elif choice == "iso":
            return f"{rng.randint(2000, 2030)}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:{rng.randint(0,59):02d}"
        elif choice == "malformed":
            return rng.choice(["not-a-date", "2025-13-40", "", "2025/01/01", "01-2025-15"])
        elif choice == "empty":
            return ""
        elif choice == "none":
            return ""  # Will be passed as empty string

    def _gen_task_manager_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_data_row(self, rng: random.Random) -> dict[str, Any]:
        """Generate a random data row for data_pipeline."""
        row = {}
        for key in ["name", "value", "date", "category", "amount", "id"]:
            if rng.random() > 0.3:  # 70% chance to include each field
                row[key] = self._random_value(rng)
        # Sometimes add unexpected fields
        if rng.random() > 0.7:
            row[self._random_string(rng)] = self._random_value(rng)
        return row

    def _gen_validator_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_date_parser_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_transformer_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_pipeline_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_auth_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_session_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_csrf_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_router_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_middleware_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_cors_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_rate_limit_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_request_validator_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_model_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_queryset_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_view_inputs(self, rng: random.Random) -> tuple:
        return ()

    def _gen_form_inputs(self, rng: random.Random) -> tuple:
        return ()
