"""Sandbox module — Docker-based isolated execution.

Provides:
- SandboxManager for container lifecycle management
- SandboxExecutor for command execution inside containers
- SandboxPolicy with security policies (non-root, no network, resource limits)
- Workspace reset and cleanup
- Fail-closed security: no Docker means clear error, never fallback to host
"""

__version__ = "0.1.0"

from forge.sandbox.executor import SandboxExecutor
from forge.sandbox.manager import SandboxManager
from forge.sandbox.policies import SandboxPolicy, get_default_policy, get_relaxed_policy, get_strict_policy
from forge.sandbox.reset import cleanup_workspace, create_fresh_workspace, reset_workspace
from forge.sandbox.network import NetworkPolicyManager, NetworkPolicy, NetworkPolicyResult
from forge.sandbox.image_validation import ImageValidator, ImageValidationResult

__all__ = [
    "SandboxManager",
    "SandboxExecutor",
    "SandboxPolicy",
    "get_default_policy",
    "get_relaxed_policy",
    "get_strict_policy",
    "reset_workspace",
    "cleanup_workspace",
    "create_fresh_workspace",
    "NetworkPolicyManager",
    "NetworkPolicy",
    "NetworkPolicyResult",
    "ImageValidator",
    "ImageValidationResult",
]
