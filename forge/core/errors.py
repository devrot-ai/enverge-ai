"""Exception hierarchy for ForgeLab.

All ForgeLab-specific exceptions inherit from ForgeLabError.
"""

from __future__ import annotations

from typing import Any


class ForgeLabError(Exception):
    """Base exception for all ForgeLab errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# World / Environment Errors
# ---------------------------------------------------------------------------


class WorldError(ForgeLabError):
    """Base error for world-related operations."""


class WorldGenerationError(WorldError):
    """Raised when world generation fails."""


class WorldValidationError(WorldError):
    """Raised when world validation fails."""


class WorldResetError(WorldError):
    """Raised when world reset fails."""


class TemplateNotFoundError(WorldError):
    """Raised when a world template is not found."""


# ---------------------------------------------------------------------------
# Task Errors
# ---------------------------------------------------------------------------


class TaskError(ForgeLabError):
    """Base error for task-related operations."""


class TaskGenerationError(TaskError):
    """Raised when task generation fails."""


class TaskValidationError(TaskError):
    """Raised when task validation fails."""


class TaskNotFoundError(TaskError):
    """Raised when a task is not found."""


# ---------------------------------------------------------------------------
# Agent Errors
# ---------------------------------------------------------------------------


class AgentError(ForgeLabError):
    """Base error for agent-related operations."""


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""


class AgentTimeoutError(AgentError):
    """Raised when an agent exceeds its time limit."""


class AgentStepLimitError(AgentError):
    """Raised when an agent exceeds its step limit."""


class ToolExecutionError(AgentError):
    """Raised when a tool call fails."""


class PathTraversalError(AgentError):
    """Raised when a tool call attempts path traversal outside the workspace."""


# ---------------------------------------------------------------------------
# Sandbox Errors
# ---------------------------------------------------------------------------


class SandboxError(ForgeLabError):
    """Base error for sandbox-related operations."""


class SandboxCreationError(SandboxError):
    """Raised when sandbox container creation fails."""


class SandboxExecutionError(SandboxError):
    """Raised when command execution in sandbox fails."""


class SandboxUnavailableError(SandboxError):
    """Raised when Docker is not available."""


# ---------------------------------------------------------------------------
# Verification Errors
# ---------------------------------------------------------------------------


class VerificationError(ForgeLabError):
    """Base error for verification-related operations."""


class VerifierFailureError(VerificationError):
    """Raised when the verifier itself is defective."""


# ---------------------------------------------------------------------------
# Diagnosis Errors
# ---------------------------------------------------------------------------


class DiagnosisError(ForgeLabError):
    """Base error for diagnosis-related operations."""


# ---------------------------------------------------------------------------
# Curriculum Errors
# ---------------------------------------------------------------------------


class CurriculumError(ForgeLabError):
    """Base error for curriculum-related operations."""


class TaskSelectionError(CurriculumError):
    """Raised when task selection fails."""


# ---------------------------------------------------------------------------
# Experiment Errors
# ---------------------------------------------------------------------------


class ExperimentError(ForgeLabError):
    """Base error for experiment-related operations."""


class ExperimentNotFoundError(ExperimentError):
    """Raised when an experiment is not found."""


# ---------------------------------------------------------------------------
# Database Errors
# ---------------------------------------------------------------------------


class DatabaseError(ForgeLabError):
    """Base error for database operations."""


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""


# ---------------------------------------------------------------------------
# Configuration Errors
# ---------------------------------------------------------------------------


class ConfigError(ForgeLabError):
    """Base error for configuration issues."""


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""
