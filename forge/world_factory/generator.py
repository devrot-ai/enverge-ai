"""World factory: generates executable software environments.

Creates Python repositories from templates with deterministic bug injection.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from forge.core.errors import (
    TemplateNotFoundError,
    WorldGenerationError,
)
from forge.core.schemas import WorldSpec
from forge.world_factory.seeder import apply_mutation, get_mutation, list_mutations
from forge.world_factory.templates import get_template, list_templates

logger = logging.getLogger(__name__)


class WorldGenerator:
    """Generates executable software environments from templates.

    Each generated world is a reproducible, isolated Python repository
    with a deliberately injected defect.

    Attributes:
        output_dir: Directory where generated worlds are stored.
    """

    def __init__(self, output_dir: str | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "forgelab_worlds"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        template_name: str,
        mutation_id: str,
        seed: int | None = None,
        world_id: str | None = None,
    ) -> WorldSpec:
        """Generate a world from a template with a specific mutation.

        Args:
            template_name: Name of the world template.
            mutation_id: ID of the mutation to inject.
            seed: Random seed for reproducibility.
            world_id: Optional pre-assigned world ID.

        Returns:
            WorldSpec describing the generated world.

        Raises:
            TemplateNotFoundError: If the template doesn't exist.
            WorldGenerationError: If generation fails.
        """
        # Validate template exists
        if not get_template(template_name):
            available = list_templates()
            raise TemplateNotFoundError(f"Template '{template_name}' not found. Available: {available}")

        # Validate mutation exists
        mutation = get_mutation(mutation_id)
        if mutation is None:
            available = list_mutations()
            raise WorldGenerationError(f"Mutation '{mutation_id}' not found. Available: {available}")

        # Create world directory
        wid = world_id or f"world-{seed or 0}-{template_name}-{mutation_id}"
        world_dir = self.output_dir / wid
        world_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy template files
            template = get_template(template_name)
            for filename, content in template["files"].items():
                dest = world_dir / filename
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content)

            # Apply mutation
            mutated_files = apply_mutation(world_dir, mutation_id)

            # Initialize git repo and create initial commit
            initial_commit = self._init_git(world_dir, wid)

            # Generate manifest
            manifest = self._generate_manifest(
                world_dir, wid, template_name, mutation_id, seed, initial_commit, mutated_files
            )
            manifest_path = world_dir / ".forgelab_manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2))

            # Create WorldSpec
            spec = WorldSpec(
                world_id=wid,
                world_type="python_repository",
                template_name=template_name,
                template_version=template.get("version", "0.1"),
                seed=seed,
                mutation_id=mutation_id,
                initial_commit=initial_commit,
                dependencies=template.get("dependencies", []),
                metadata={
                    "world_dir": str(world_dir),
                    "mutated_files": mutated_files,
                },
            )

            logger.info(f"Generated world {wid} from template '{template_name}' with mutation '{mutation_id}'")
            return spec

        except Exception as e:
            # Clean up on failure
            if world_dir.exists():
                shutil.rmtree(world_dir, ignore_errors=True)
            raise WorldGenerationError(f"Failed to generate world: {e}") from e

    def _init_git(self, world_dir: Path, world_id: str) -> str:
        """Initialize a git repository and create the initial commit.

        Args:
            world_dir: Path to the world directory.
            world_id: World identifier for commit message.

        Returns:
            Git commit hash of the initial state.
        """
        try:
            # Check if git is available
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                check=True,
                timeout=5,
            )

            # Initialize repo
            subprocess.run(
                ["git", "init"],
                cwd=world_dir,
                capture_output=True,
                check=True,
                timeout=10,
            )

            # Configure git user for commit
            subprocess.run(
                ["git", "config", "user.email", "forgelab@localhost"],
                cwd=world_dir,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "ForgeLab"],
                cwd=world_dir,
                capture_output=True,
                check=True,
            )

            # Add all files
            subprocess.run(
                ["git", "add", "."],
                cwd=world_dir,
                capture_output=True,
                check=True,
                timeout=10,
            )

            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", f"Initial state for {world_id}"],
                cwd=world_dir,
                capture_output=True,
                check=True,
                timeout=10,
            )

            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=world_dir,
                capture_output=True,
                check=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()

        except FileNotFoundError:
            logger.warning("Git not found, skipping repository initialization")
            return self._compute_hash(world_dir)
        except subprocess.TimeoutExpired:
            logger.warning("Git operation timed out, using hash instead")
            return self._compute_hash(world_dir)
        except subprocess.CalledProcessError:
            logger.warning("Git commit failed, using hash instead")
            return self._compute_hash(world_dir)

    def _compute_hash(self, world_dir: Path) -> str:
        """Compute a deterministic hash of the world directory contents.

        Args:
            world_dir: Path to the world directory.

        Returns:
            Hex hash string.
        """
        h = hashlib.sha256()
        for root, dirs, files in sorted(os.walk(world_dir)):
            for f in sorted(files):
                fp = Path(root) / f
                if fp.name == ".forgelab_manifest.json":
                    continue
                try:
                    h.update(fp.read_bytes())
                except (OSError, PermissionError):
                    pass
        return h.hexdigest()[:12]

    def _generate_manifest(
        self,
        world_dir: Path,
        world_id: str,
        template_name: str,
        mutation_id: str,
        seed: int | None,
        initial_commit: str,
        mutated_files: list[str],
    ) -> dict[str, Any]:
        """Generate a world manifest for tracking.

        Args:
            world_dir: Path to the world directory.
            world_id: World identifier.
            template_name: Template used.
            mutation_id: Mutation applied.
            seed: Random seed.
            initial_commit: Git commit hash.
            mutated_files: List of files that were mutated.

        Returns:
            Manifest dictionary.
        """
        return {
            "world_id": world_id,
            "template_name": template_name,
            "mutation_id": mutation_id,
            "seed": seed,
            "initial_commit": initial_commit,
            "mutated_files": mutated_files,
            "world_dir": str(world_dir),
            "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        }

    def _remove_directory(self, dir_path: Path) -> bool:
        """Remove a directory, handling Git locks on Windows.

        Args:
            dir_path: Path to the directory.

        Returns:
            True if removal succeeded.
        """
        if not dir_path.exists():
            return True
        try:
            # On Windows, Git may lock files. Remove lock files first.
            git_dir = dir_path / ".git"
            if git_dir.exists():
                # Remove index.lock if it exists
                index_lock = git_dir / "index.lock"
                if index_lock.exists():
                    try:
                        index_lock.unlink()
                    except (OSError, PermissionError):
                        pass
                # Remove any other lock files
                for lock_file in git_dir.rglob("*.lock"):
                    try:
                        lock_file.unlink()
                    except (OSError, PermissionError):
                        pass

            # Try standard removal first
            shutil.rmtree(dir_path, ignore_errors=True)

            # If still exists, try aggressive removal
            if dir_path.exists():
                import time

                time.sleep(0.2)  # Brief pause for file handle release
                for attempt in range(3):
                    for item in sorted(dir_path.rglob("*"), reverse=True):
                        if item.is_file():
                            try:
                                item.chmod(0o666)
                                item.unlink(missing_ok=True)
                            except (OSError, PermissionError):
                                pass
                    try:
                        for subdir in sorted(dir_path.iterdir(), reverse=True):
                            if subdir.is_dir():
                                try:
                                    shutil.rmtree(subdir, ignore_errors=True)
                                except (OSError, PermissionError):
                                    pass
                            else:
                                try:
                                    subdir.unlink(missing_ok=True)
                                except (OSError, PermissionError):
                                    pass
                    except (OSError, PermissionError):
                        pass
                    if not dir_path.exists():
                        break
                    time.sleep(0.1)
                try:
                    dir_path.rmdir()
                except (OSError, PermissionError):
                    pass

            return not dir_path.exists()
        except Exception as e:
            logger.warning(f"Failed to remove directory {dir_path}: {e}")
            return False

    def reset_world(self, world_spec: WorldSpec) -> bool:
        """Reset a world to its initial state by regenerating it.

        Args:
            world_spec: The world specification.

        Returns:
            True if reset was successful.
        """
        if world_spec.mutation_id and world_spec.template_name:
            try:
                # Remove existing world
                world_dir = Path(world_spec.metadata.get("world_dir", ""))
                if world_dir.exists():
                    self._remove_directory(world_dir)

                # Regenerate
                self.generate(
                    template_name=world_spec.template_name,
                    mutation_id=world_spec.mutation_id,
                    seed=world_spec.seed,
                    world_id=world_spec.world_id,
                )
                return True
            except Exception as e:
                logger.error(f"Failed to reset world {world_spec.world_id}: {e}")
                return False
        return False

    def cleanup_world(self, world_spec: WorldSpec) -> bool:
        """Remove a generated world from disk.

        Args:
            world_spec: The world specification.

        Returns:
            True if cleanup was successful.
        """
        world_dir = Path(world_spec.metadata.get("world_dir", ""))
        return self._remove_directory(world_dir)
