"""Training module — adapter interface for ML training integration.

Provides:
- TrainingAdapter interface for connecting to external trainers
- TrajectoryExporter for normalized trajectory export
- TrajectoryNormalizer for converting to standard JSONL format
- RewardComputer for computing reward signals
- DatasetVersioner for versioned datasets
- ExampleCurator for positive/negative example curation
- TRLTrainer for Hugging Face TRL integration
- GRPOTrainer for Group Relative Policy Optimization
- AgentLightningClient for Microsoft Agent Lightning
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

# Optional imports — available when ML dependencies are installed
try:
    from forge.training.trl_integration import TRLConfig, TRLTrainer
except ImportError:
    TRLConfig = None  # type: ignore[misc,assignment]
    TRLTrainer = None  # type: ignore[misc,assignment]

try:
    from forge.training.grpo import GRPOConfig, GRPOTrainer
except ImportError:
    GRPOConfig = None  # type: ignore[misc,assignment]
    GRPOTrainer = None  # type: ignore[misc,assignment]

try:
    from forge.training.agent_lightning import (
        AgentLightningClient,
        AgentLightningConfig,
    )
except ImportError:
    AgentLightningClient = None  # type: ignore[misc,assignment]
    AgentLightningConfig = None  # type: ignore[misc,assignment]

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
    "TRLConfig",
    "TRLTrainer",
    "GRPOConfig",
    "GRPOTrainer",
    "AgentLightningClient",
    "AgentLightningConfig",
]
