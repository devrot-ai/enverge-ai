"""ForgeLab — Adaptive Environment Factory for Autonomous Agents.

ForgeLab generates software engineering tasks, executes autonomous agents
in isolated environments, independently verifies their results, diagnoses
failures, and uses verified outcomes to improve future task generation.

https://github.com/forgelab-llm/forgelab
"""

__version__ = "0.1.0"
__author__ = "ForgeLab Contributors"
__license__ = "MIT"

# Core exports
from forge.core.config import get_config, load_config
from forge.core.errors import ForgeLabError
from forge.core.events import EventEmitter
from forge.core.registry import Registry
from forge.core.schemas import (
    AgentConfig,
    CurriculumState,
    CurriculumStrategy,
    ExperimentConfig,
    FailureCategory,
    FailureDiagnosis,
    RunConfig,
    RunResult,
    RunStatus,
    TaskCategory,
    TaskSpec,
    Trajectory,
    TrajectoryStep,
    ValidationStatus,
    VerificationResult,
    WorldSpec,
)

__all__ = [
    # Version
    "__version__",
    # Schemas
    "WorldSpec",
    "TaskSpec",
    "AgentConfig",
    "RunConfig",
    "RunResult",
    "Trajectory",
    "TrajectoryStep",
    "VerificationResult",
    "FailureDiagnosis",
    "CurriculumState",
    "ExperimentConfig",
    "TaskCategory",
    "FailureCategory",
    "RunStatus",
    "ValidationStatus",
    "CurriculumStrategy",
    # Core utilities
    "ForgeLabError",
    "get_config",
    "load_config",
    "Registry",
    "EventEmitter",
]
