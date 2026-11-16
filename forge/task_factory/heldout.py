"""Held-out evaluation set manager.

Creates a frozen set of tasks for benchmarking that the generator never sees.
These tasks are excluded from curriculum selection by default.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from forge.core.schemas import TaskCategory, TaskSpec
from forge.world_factory.generator import WorldGenerator


class HeldOutManager:
    """Manages a held-out set of frozen benchmark tasks.

    These tasks are generated once and stored for consistent benchmarking.
    They are excluded from adaptive curriculum selection.
    """

    def __init__(self, heldout_dir: Path | None = None):
        """Initialize the held-out manager.

        Args:
            heldout_dir: Directory to store held-out tasks. Defaults to datasets/heldout/.
        """
        self.heldout_dir = heldout_dir or Path("datasets/heldout")
        self.heldout_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.heldout_dir / "index.json"
        self._index = self._load_index()

    def create_heldout_set(self, size: int = 10) -> list[TaskSpec]:
        """Create a held-out set of tasks.

        Args:
            size: Number of tasks to generate.

        Returns:
            List of TaskSpec objects for the held-out set.
        """
        generator = WorldGenerator()
        tasks = []

        templates = ["task_manager_api", "data_pipeline", "flask_app", "express_api", "django_app"]
        for i in range(size):
            template = templates[i % len(templates)]
            world = generator.generate(template, seed=1000 + i)

            task = TaskSpec(
                task_id=f"heldout-{i+1:03d}",
                world_id=world.world_id,
                category=TaskCategory.BUG_REPAIR,
                description=f"Held-out task {i+1}: Fix the bug in {template}",
                difficulty_level=(i % 5) + 1,
                capabilities=["debugging", "code_repair"],
                metadata={
                    "heldout": True,
                    "template": template,
                    "mutation": world.mutation_id,
                    "seed": 1000 + i,
                },
            )
            tasks.append(task)

        # Save tasks
        for task in tasks:
            self._save_task(task)

        # Update index
        self._save_index()
        return tasks

    def get_heldout_tasks(self) -> list[TaskSpec]:
        """Get all held-out tasks.

        Returns:
            List of TaskSpec objects.
        """
        tasks = []
        for task_file in self.heldout_dir.glob("task-*.json"):
            try:
                data = json.loads(task_file.read_text())
                task = TaskSpec.from_dict(data)
                tasks.append(task)
            except Exception:
                continue
        return tasks

    def is_heldout(self, task_id: str) -> bool:
        """Check if a task is in the held-out set.

        Args:
            task_id: The task ID to check.

        Returns:
            True if the task is in the held-out set.
        """
        return task_id in self._index.get("task_ids", [])

    def _save_task(self, task: TaskSpec) -> None:
        """Save a task to the held-out directory.

        Args:
            task: The task to save.
        """
        task_file = self.heldout_dir / f"{task.task_id}.json"
        task_file.write_text(json.dumps(task.to_dict(), indent=2, default=str))

    def _load_index(self) -> dict[str, Any]:
        """Load the held-out index.

        Returns:
            Index dict with task IDs and metadata.
        """
        if self._index_path.exists():
            return json.loads(self._index_path.read_text())
        return {"task_ids": [], "created_at": None, "size": 0}

    def _save_index(self) -> None:
        """Save the held-out index."""
        self._index["task_ids"] = [f.stem for f in self.heldout_dir.glob("task-*.json")]
        self._index["size"] = len(self._index["task_ids"])
        self._index["created_at"] = datetime.utcnow().isoformat()
        self._index_path.write_text(json.dumps(self._index, indent=2))
