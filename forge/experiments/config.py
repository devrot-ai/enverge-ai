"""Experiment configuration management.

Provides helper functions to create and manage experiment configurations.
"""

from __future__ import annotations

from typing import Any

from forge.core.schemas import CurriculumStrategy, ExperimentConfig


def create_experiment_a_config(
    name: str = "static-vs-adaptive",
    **kwargs: Any,
) -> ExperimentConfig:
    """Create configuration for Experiment A: Static vs Adaptive Curriculum.

    Args:
        name: Experiment name.
        **kwargs: Additional configuration overrides.

    Returns:
        ExperimentConfig for Experiment A.
    """
    config = ExperimentConfig(
        name=name,
        description="Compare fixed task sequence vs failure-targeted adaptive curriculum",
        hypothesis="H1: Adaptive task generation produces more useful learning experiences",
        task_selection_strategy=CurriculumStrategy.ADAPTIVE,
        metadata={
            "experiment_type": "A",
            "comparison": "static_vs_adaptive",
        },
        **kwargs,
    )
    return config


def create_experiment_b_config(
    name: str = "random-vs-validated",
    **kwargs: Any,
) -> ExperimentConfig:
    """Create configuration for Experiment B: Random vs Validated Environments.

    Args:
        name: Experiment name.
        **kwargs: Additional configuration overrides.

    Returns:
        ExperimentConfig for Experiment B.
    """
    config = ExperimentConfig(
        name=name,
        description="Compare unvalidated vs fully validated task generation",
        hypothesis="H2: Independent environment validation reduces misleading failure signals",
        task_selection_strategy=CurriculumStrategy.RANDOM,
        metadata={
            "experiment_type": "B",
            "comparison": "random_vs_validated",
        },
        **kwargs,
    )
    return config


def create_experiment_c_config(
    name: str = "generic-vs-targeted",
    **kwargs: Any,
) -> ExperimentConfig:
    """Create configuration for Experiment C: Generic vs Targeted Challenges.

    Args:
        name: Experiment name.
        **kwargs: Additional configuration overrides.

    Returns:
        ExperimentConfig for Experiment C.
    """
    config = ExperimentConfig(
        name=name,
        description="Compare random coding problems vs weakness-focused challenges",
        hypothesis="H3: Targeted task generation improves agent capability on related unseen tasks",
        task_selection_strategy=CurriculumStrategy.ADAPTIVE,
        metadata={
            "experiment_type": "C",
            "comparison": "generic_vs_targeted",
        },
        **kwargs,
    )
    return config


def create_experiment_d_config(
    name: str = "single-vs-independent-verification",
    **kwargs: Any,
) -> ExperimentConfig:
    """Create configuration for Experiment D: Single vs Independent Verification.

    Args:
        name: Experiment name.
        **kwargs: Additional configuration overrides.

    Returns:
        ExperimentConfig for Experiment D.
    """
    config = ExperimentConfig(
        name=name,
        description="Compare generator-only verification vs independent verification",
        hypothesis="H4: Independent verification improves training-data quality",
        task_selection_strategy=CurriculumStrategy.STATIC,
        metadata={
            "experiment_type": "D",
            "comparison": "single_vs_independent_verification",
        },
        **kwargs,
    )
    return config


def get_preset_experiments() -> dict[str, ExperimentConfig]:
    """Get all preset experiment configurations.

    Returns:
        Dictionary mapping experiment type to config.
    """
    return {
        "A": create_experiment_a_config(),
        "B": create_experiment_b_config(),
        "C": create_experiment_c_config(),
        "D": create_experiment_d_config(),
    }
