"""Integration tests for seed task loading and world generation.

Verifies all 8 seed tasks from datasets/seeds/seed_tasks.yaml can be
loaded and have worlds generated correctly.
"""

import tempfile
from pathlib import Path

from forge.task_factory.generator import TaskGenerator


class TestSeedTaskLoader:
    """Test the seed task loader reads all 8 seed tasks correctly."""

    def test_load_seed_tasks_count(self):
        """Should load 8 seed tasks."""
        seed_file = Path(__file__).parent.parent / "datasets" / "seeds" / "seed_tasks.yaml"
        gen = TaskGenerator()
        tasks = gen.load_seed_tasks(str(seed_file))
        assert len(tasks) == 8

    def test_load_seed_task_ids(self):
        """Should load all expected task IDs."""
        seed_file = Path(__file__).parent.parent / "datasets" / "seeds" / "seed_tasks.yaml"
        gen = TaskGenerator()
        tasks = gen.load_seed_tasks(str(seed_file))
        task_ids = {t.task_id for t in tasks}
        expected = {
            "PY-REPAIR-001",
            "PY-REPAIR-002",
            "PY-REPAIR-003",
            "PY-REPAIR-004",
            "PY-REPAIR-005",
            "PY-REPAIR-006",
            "PY-REPAIR-007",
            "PY-REPAIR-008",
        }
        assert task_ids == expected

    def test_load_seed_task_fields(self):
        """Each seed task should have required fields."""
        seed_file = Path(__file__).parent.parent / "datasets" / "seeds" / "seed_tasks.yaml"
        gen = TaskGenerator()
        tasks = gen.load_seed_tasks(str(seed_file))
        for task in tasks:
            assert task.task_id
            assert task.description
            assert task.difficulty_level is not None
            assert task.constraints is not None

    def test_load_seed_task_templates(self):
        """Seed tasks should reference valid templates."""
        seed_file = Path(__file__).parent.parent / "datasets" / "seeds" / "seed_tasks.yaml"
        gen = TaskGenerator()
        tasks = gen.load_seed_tasks(str(seed_file))
        templates = {t.metadata.get("template") for t in tasks if t.metadata}
        valid_templates = {
            "task_manager_api",
            "data_pipeline",
            "flask_app",
            "express_api",
            "django_app",
        }
        assert templates.issubset(valid_templates)

    def test_load_missing_file(self):
        """Loading a non-existent file should return empty list."""
        gen = TaskGenerator()
        tasks = gen.load_seed_tasks("/nonexistent/path.yaml")
        assert tasks == []


class TestSeedTaskWorldGeneration:
    """Test that each seed task can generate a valid world."""

    def _check_world(self, mutation: str, template: str):
        """Generate a world and check files exist within the temp dir context."""
        from forge.world_factory.generator import WorldGenerator

        with tempfile.TemporaryDirectory() as td:
            generator = WorldGenerator(output_dir=td)
            world_spec = generator.generate(
                template_name=template,
                mutation_id=mutation,
                seed=42,
            )
            world_dir = generator.output_dir / world_spec.world_id
            assert world_spec is not None
            assert world_dir.exists(), f"World dir {world_dir} does not exist"
            # data_pipeline uses pipeline.py; others use app.py
            main_file = "pipeline.py" if template == "data_pipeline" else "app.py"
            assert (world_dir / main_file).exists(), f"{main_file} not found in {world_dir}"
            assert (world_dir / "tests" / "test_public.py").exists()
            assert (world_dir / ".hidden_tests" / "test_hidden.py").exists()

    def test_py_repair_001_task_manager_api(self):
        """PY-REPAIR-001: pagination_boundary on task_manager_api."""
        self._check_world("pagination_boundary", "task_manager_api")

    def test_py_repair_002_task_manager_api(self):
        """PY-REPAIR-002: empty_search on task_manager_api."""
        self._check_world("empty_search", "task_manager_api")

    def test_py_repair_003_task_manager_api(self):
        """PY-REPAIR-003: duplicate_records on task_manager_api."""
        self._check_world("duplicate_records", "task_manager_api")

    def test_py_repair_004_flask_app(self):
        """PY-REPAIR-004: session_timeout on flask_app."""
        self._check_world("session_timeout", "flask_app")

    def test_py_repair_005_flask_app(self):
        """PY-REPAIR-005: password_hash on flask_app."""
        self._check_world("password_hash", "flask_app")

    def test_py_repair_006_data_pipeline(self):
        """PY-REPAIR-006: null_handling on data_pipeline."""
        self._check_world("null_handling", "data_pipeline")

    def test_py_repair_007_data_pipeline(self):
        """PY-REPAIR-007: date_parsing on data_pipeline."""
        self._check_world("date_parsing", "data_pipeline")

    def test_py_repair_008_data_pipeline(self):
        """PY-REPAIR-008: duplicate_detection on data_pipeline."""
        self._check_world("duplicate_detection", "data_pipeline")
