"""Tests for the world factory module."""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from forge.core.errors import TemplateNotFoundError, WorldGenerationError
from forge.world_factory.generator import WorldGenerator
from forge.world_factory.manifest import has_manifest, read_manifest, write_manifest
from forge.world_factory.seeder import (
    apply_mutation,
    get_mutation,
    get_reference_fix,
    list_mutations,
    revert_mutation,
)
from forge.world_factory.templates import get_template, list_templates


class TestTemplates:
    def test_task_manager_api_registered(self):
        template = get_template("task_manager_api")
        assert template is not None
        assert "files" in template
        assert "app.py" in template["files"]

    def test_list_templates(self):
        templates = list_templates()
        assert "task_manager_api" in templates

    def test_template_has_hidden_tests(self):
        template = get_template("task_manager_api")
        files = template["files"]
        assert ".hidden_tests/test_hidden.py" in files

    def test_template_has_reference_solution(self):
        template = get_template("task_manager_api")
        files = template["files"]
        assert ".reference_solution.py" in files

    def test_get_nonexistent_template(self):
        assert get_template("nonexistent") is None


class TestMutations:
    def test_pagination_boundary_registered(self):
        mutation = get_mutation("pagination_boundary")
        assert mutation is not None
        assert mutation["target_file"] == "app.py"

    def test_empty_search_registered(self):
        mutation = get_mutation("empty_search")
        assert mutation is not None

    def test_duplicate_records_registered(self):
        mutation = get_mutation("duplicate_records")
        assert mutation is not None

    def test_list_mutations(self):
        mutations = list_mutations()
        assert "pagination_boundary" in mutations
        assert "empty_search" in mutations
        assert "duplicate_records" in mutations

    def test_get_nonexistent_mutation(self):
        assert get_mutation("nonexistent") is None

    def test_reference_fix_available(self):
        fix = get_reference_fix("pagination_boundary")
        assert fix is not None
        assert "start = (page - 1) * page_size" in fix


class TestMutationApplication:
    @pytest.fixture()
    def world_dir(self):
        """Create a temporary world with the task_manager_api template."""
        tmpdir = tempfile.mkdtemp()
        template = get_template("task_manager_api")
        for filename, content in template["files"].items():
            dest = Path(tmpdir) / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        yield Path(tmpdir)
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_apply_pagination_boundary(self, world_dir):
        mutated = apply_mutation(world_dir, "pagination_boundary")
        assert "app.py" in mutated
        content = (world_dir / "app.py").read_text()
        assert "raise IndexError" in content

    def test_apply_empty_search(self, world_dir):
        mutated = apply_mutation(world_dir, "empty_search")
        assert "app.py" in mutated
        content = (world_dir / "app.py").read_text()
        assert "filtered = []" in content

    def test_apply_duplicate_records(self, world_dir):
        mutated = apply_mutation(world_dir, "duplicate_records")
        assert "app.py" in mutated
        content = (world_dir / "app.py").read_text()
        assert "Skip tasks with duplicate titles" in content

    def test_revert_mutation(self, world_dir):
        apply_mutation(world_dir, "pagination_boundary")
        reverted = revert_mutation(world_dir, "pagination_boundary")
        assert "app.py" in reverted
        content = (world_dir / "app.py").read_text()
        assert "raise IndexError" not in content

    def test_apply_nonexistent_mutation(self, world_dir):
        with pytest.raises(FileNotFoundError):
            apply_mutation(world_dir, "nonexistent")


class TestWorldGenerator:
    @pytest.fixture()
    def output_dir(self):
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_generate_world(self, output_dir):
        gen = WorldGenerator(output_dir)
        spec = gen.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=42,
        )
        assert spec.world_type == "python_repository"
        assert spec.mutation_id == "pagination_boundary"
        assert spec.seed == 42
        world_dir = Path(spec.metadata["world_dir"])
        assert world_dir.exists()
        assert (world_dir / "app.py").exists()

    def test_generate_world_has_manifest(self, output_dir):
        gen = WorldGenerator(output_dir)
        spec = gen.generate(
            template_name="task_manager_api",
            mutation_id="empty_search",
            seed=1,
        )
        world_dir = Path(spec.metadata["world_dir"])
        assert has_manifest(world_dir)

    def test_generate_nonexistent_template(self, output_dir):
        gen = WorldGenerator(output_dir)
        with pytest.raises(TemplateNotFoundError):
            gen.generate(
                template_name="nonexistent",
                mutation_id="pagination_boundary",
            )

    def test_generate_nonexistent_mutation(self, output_dir):
        gen = WorldGenerator(output_dir)
        with pytest.raises(WorldGenerationError):
            gen.generate(
                template_name="task_manager_api",
                mutation_id="nonexistent",
            )

    def test_deterministic_generation(self, output_dir):
        gen = WorldGenerator(output_dir)
        spec1 = gen.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=42,
            world_id="test-deterministic",
        )
        world_dir = Path(spec1.metadata["world_dir"])
        content1 = (world_dir / "app.py").read_text()

        # Clean and regenerate using generator's cleanup
        gen.cleanup_world(spec1)
        import time

        time.sleep(0.5)  # Windows file system sync
        spec2 = gen.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=42,
            world_id="test-deterministic",
        )
        content2 = (world_dir / "app.py").read_text()
        assert content1 == content2

    def test_cleanup_world(self, output_dir):
        gen = WorldGenerator(output_dir)
        spec = gen.generate(
            template_name="task_manager_api",
            mutation_id="pagination_boundary",
            seed=42,
        )
        world_dir = Path(spec.metadata["world_dir"])
        assert world_dir.exists()
        result = gen.cleanup_world(spec)
        # cleanup returns True if directory was removed or didn't exist
        assert result is True


class TestManifest:
    @pytest.fixture()
    def world_dir(self):
        tmpdir = tempfile.mkdtemp()
        yield Path(tmpdir)
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_write_and_read_manifest(self, world_dir):
        data = {"world_id": "test-123", "seed": 42}
        write_manifest(world_dir, data)
        result = read_manifest(world_dir)
        assert result["world_id"] == "test-123"
        assert result["seed"] == 42

    def test_has_manifest(self, world_dir):
        assert not has_manifest(world_dir)
        write_manifest(world_dir, {})
        assert has_manifest(world_dir)

    def test_read_nonexistent_manifest(self, world_dir):
        assert read_manifest(world_dir) is None
