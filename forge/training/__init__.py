"""Training module — adapter interface for future RL integration.

Provides:
- TrainingAdapter interface for connecting to external trainers
- TrajectoryExporter for normalized trajectory export
- TrajectoryNormalizer for converting to standard JSONL format
- RewardComputer for computing reward signals
- DatasetVersioner for versioned datasets
- ExampleCurator for positive/negative example curation
- Support for Hugging Face TRL, GRPO, PPO, Agent Lightning (future)
"""

__version__ = "0.1.0"

from forge.training.adapter import NoOpTrainingAdapter, TrainingAdapter, TrajectoryExporter
from forge.training.versioning import DatasetVersion, DatasetVersioner
from forge.training.curator import CuratedExample, ExampleCurator
from forge.training.adapter import TrajectoryFilter
from forge.training.normalized import (
    NormalizedTrajectory,
    SCHEMA_VERSION,
    TrajectoryNormalizer,
)
from forge.training.rewards import RewardComputer, RewardSignal

__all__ = [
    "TrainingAdapter",
    "TrajectoryExporter",
    "NoOpTrainingAdapter",
    "TrajectoryFilter",
    "DatasetVersion",
    "DatasetVersioner",
    "CuratedExample",
    "ExampleCurator",
    "NormalizedTrajectory",
    "SCHEMA_VERSION",
    "TrajectoryNormalizer",
    "RewardComputer",
    "RewardSignal",
]
