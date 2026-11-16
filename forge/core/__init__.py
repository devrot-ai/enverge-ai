"""Core module — shared data structures, interfaces, configuration, events, and registries.

This module provides the foundation for all ForgeLab components:
- Typed data schemas (WorldSpec, TaskSpec, RunResult, etc.)
- Configuration loading from YAML and environment variables
- Explicit exception hierarchy
- Pipeline event emitter
- Pluggable component registry
"""

__version__ = "0.1.0"

from forge.core.config import get_config, load_config
from forge.core.errors import (
    AgentError,
    AgentExecutionError,
    AgentStepLimitError,
    AgentTimeoutError,
    ConfigError,
    ConfigValidationError,
    CurriculumError,
    DatabaseConnectionError,
    DatabaseError,
    DiagnosisError,
    ExperimentError,
    ExperimentNotFoundError,
    ForgeLabError,
    PathTraversalError,
    SandboxCreationError,
    SandboxError,
    SandboxExecutionError,
    SandboxUnavailableError,
    TaskError,
    TaskGenerationError,
    TaskNotFoundError,
    TaskSelectionError,
    TaskValidationError,
    TemplateNotFoundError,
    ToolExecutionError,
    VerificationError,
    VerifierFailureError,
    WorldError,
    WorldGenerationError,
    WorldResetError,
    WorldValidationError,
)
from forge.core.audit import AuditEntry, AuditLogger
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
    generate_id,
)

__all__ = [
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
    "generate_id",
    # Errors
    "ForgeLabError",
    "WorldError",
    "WorldGenerationError",
    "WorldValidationError",
    "WorldResetError",
    "TemplateNotFoundError",
    "TaskError",
    "TaskGenerationError",
    "TaskValidationError",
    "TaskNotFoundError",
    "AgentError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "AgentStepLimitError",
    "ToolExecutionError",
    "PathTraversalError",
    "SandboxError",
    "SandboxCreationError",
    "SandboxExecutionError",
    "SandboxUnavailableError",
    "VerificationError",
    "VerifierFailureError",
    "DiagnosisError",
    "CurriculumError",
    "TaskSelectionError",
    "ExperimentError",
    "ExperimentNotFoundError",
    "DatabaseError",
    "DatabaseConnectionError",
    "ConfigError",
    "ConfigValidationError",
    # Config
    "load_config",
    "get_config",
    # Registry
    "Registry",
    # Events
    "EventEmitter",
    # Audit
    "AuditEntry",
    "AuditLogger",
]
