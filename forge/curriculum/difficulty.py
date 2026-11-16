"""Difficulty estimation and adjustment for curriculum tasks.

Provides functions to estimate task difficulty and adjust
difficulty based on agent performance.
"""

from __future__ import annotations

from typing import Any


def estimate_difficulty(
    capabilities: list[str],
    mutation_id: str | None = None,
    base_difficulty: int = 1,
) -> int:
    """Estimate task difficulty based on capabilities and mutation.

    Args:
        capabilities: List of capabilities the task exercises.
        mutation_id: Identifier of the bug mutation.
        base_difficulty: Base difficulty level.

    Returns:
        Difficulty level from 1 to 5.
    """
    difficulty = base_difficulty

    # More capabilities = harder
    difficulty += min(len(capabilities) - 1, 2)

    # Certain mutations are inherently harder
    hard_mutations = ["duplicate_records", "regression"]
    if mutation_id and any(hm in mutation_id for hm in hard_mutations):
        difficulty += 1

    return max(1, min(5, difficulty))


def adjust_difficulty(
    current: int,
    success_rate: float,
    min_difficulty: int = 1,
    max_difficulty: int = 5,
) -> int:
    """Adjust difficulty based on success rate.

    Args:
        current: Current difficulty level.
        success_rate: Recent success rate (0.0 to 1.0).
        min_difficulty: Minimum difficulty.
        max_difficulty: Maximum difficulty.

    Returns:
        Adjusted difficulty level.
    """
    if success_rate > 0.8:
        return min(current + 1, max_difficulty)
    elif success_rate < 0.3:
        return max(current - 1, min_difficulty)
    return current


def compute_task_complexity(task_metadata: dict[str, Any]) -> float:
    """Compute a continuous complexity score for a task.

    Args:
        task_metadata: Task metadata dictionary.

    Returns:
        Complexity score from 0.0 to 1.0.
    """
    score = 0.0

    # Difficulty level (1-5)
    difficulty = task_metadata.get("difficulty_level", 1)
    score += (difficulty - 1) / 4.0 * 0.4

    # Number of capabilities
    capabilities = task_metadata.get("capabilities", [])
    score += min(len(capabilities), 6) / 6.0 * 0.3

    # Number of constraints
    constraints = task_metadata.get("constraints", [])
    score += min(len(constraints), 5) / 5.0 * 0.2

    # Timeout (longer timeout = more complex)
    timeout = task_metadata.get("timeout_seconds", 300)
    score += min(timeout, 600) / 600.0 * 0.1

    return min(1.0, score)


def get_difficulty_label(level: int) -> str:
    """Get a human-readable label for a difficulty level.

    Args:
        level: Difficulty level (1-5).

    Returns:
        Human-readable label.
    """
    labels = {
        1: "Trivial",
        2: "Easy",
        3: "Medium",
        4: "Hard",
        5: "Expert",
    }
    return labels.get(level, f"Level {level}")


def get_difficulty_distribution(
    tasks: list[dict[str, Any]],
) -> dict[int, int]:
    """Compute the distribution of difficulty levels in a task set.

    Args:
        tasks: List of task metadata dictionaries.

    Returns:
        Dictionary mapping difficulty levels to counts.
    """
    distribution = {i: 0 for i in range(1, 6)}
    for task in tasks:
        level = task.get("difficulty_level", 1)
        if level in distribution:
            distribution[level] += 1
    return distribution
