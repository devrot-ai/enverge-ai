"""Task difficulty estimation for the task factory.

Provides functions to estimate and adjust task difficulty
based on mutation complexity and capabilities.
"""

from __future__ import annotations


def estimate_task_difficulty(
    mutation_id: str,
    capabilities: list[str],
    base_difficulty: int = 1,
) -> int:
    """Estimate task difficulty from mutation and capabilities.

    Args:
        mutation_id: Mutation identifier.
        capabilities: List of capabilities.
        base_difficulty: Base difficulty level.

    Returns:
        Difficulty level from 1 to 5.
    """
    from forge.task_factory.mutations import get_mutation

    mutation = get_mutation(mutation_id)
    if mutation:
        return mutation.difficulty

    # Fallback estimation
    difficulty = base_difficulty
    difficulty += min(len(capabilities) - 1, 2)
    return max(1, min(5, difficulty))


def adjust_task_difficulty(
    current: int,
    success_rate: float,
    min_difficulty: int = 1,
    max_difficulty: int = 5,
) -> int:
    """Adjust difficulty based on success rate.

    Args:
        current: Current difficulty level.
        success_rate: Recent success rate.
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


def get_difficulty_label(level: int) -> str:
    """Get a human-readable difficulty label.

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
