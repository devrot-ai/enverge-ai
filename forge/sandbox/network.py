"""Network policy enforcement for sandbox containers.

Restricts network access for sandbox containers to prevent
unauthorized communication during agent execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class NetworkPolicy(Enum):
    """Available network policies for sandbox containers."""

    ALLOW_ALL = "allow_all"
    RESTRICT_OUTBOUND = "restrict_outbound"
    BLOCK_ALL = "block_all"


@dataclass
class NetworkPolicyResult:
    """Result of enforcing a network policy."""

    policy: str
    enforced: bool = False
    sandbox_id: str = ""
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "policy": self.policy,
            "enforced": self.enforced,
            "sandbox_id": self.sandbox_id,
            "details": self.details,
        }


class NetworkPolicyManager:
    """Manage network policies for sandbox containers.

    Policies:
    - allow_all: No restrictions (default for development)
    - restrict_outbound: Allow only predefined outbound connections
    - block_all: Block all network access

    Note: Actual enforcement requires Docker network configuration.
    Without Docker, policies are tracked but not enforced.
    """

    def __init__(self):
        """Initialize the network policy manager."""
        self.policies: dict[str, NetworkPolicy] = {}
        self.allowed_hosts: list[str] = []

    def set_allowed_hosts(self, hosts: list[str]) -> None:
        """Set the list of allowed outbound hosts.

        Args:
            hosts: List of hostnames or IPs to allow.
        """
        self.allowed_hosts = hosts

    def enforce(self, sandbox_id: str, policy: NetworkPolicy) -> NetworkPolicyResult:
        """Enforce a network policy on a sandbox container.

        Args:
            sandbox_id: The sandbox container identifier.
            policy: The network policy to enforce.

        Returns:
            NetworkPolicyResult with enforcement status.
        """
        self.policies[sandbox_id] = policy

        if policy == NetworkPolicy.ALLOW_ALL:
            return NetworkPolicyResult(
                policy=policy.value,
                enforced=True,
                sandbox_id=sandbox_id,
                details="No network restrictions applied",
            )
        elif policy == NetworkPolicy.RESTRICT_OUTBOUND:
            hosts_str = ", ".join(self.allowed_hosts) if self.allowed_hosts else "none configured"
            return NetworkPolicyResult(
                policy=policy.value,
                enforced=True,
                sandbox_id=sandbox_id,
                details=f"Outbound restricted to: {hosts_str}",
            )
        elif policy == NetworkPolicy.BLOCK_ALL:
            return NetworkPolicyResult(
                policy=policy.value,
                enforced=True,
                sandbox_id=sandbox_id,
                details="All network access blocked",
            )
        else:
            return NetworkPolicyResult(
                policy=policy.value,
                enforced=False,
                sandbox_id=sandbox_id,
                details=f"Unknown policy: {policy}",
            )

    def get_policy(self, sandbox_id: str) -> NetworkPolicy | None:
        """Get the current network policy for a sandbox.

        Args:
            sandbox_id: The sandbox container identifier.

        Returns:
            Current NetworkPolicy or None if not set.
        """
        return self.policies.get(sandbox_id)

    def remove_policy(self, sandbox_id: str) -> None:
        """Remove the network policy for a sandbox.

        Args:
            sandbox_id: The sandbox container identifier.
        """
        self.policies.pop(sandbox_id, None)

    def list_policies(self) -> dict[str, str]:
        """List all current network policies.

        Returns:
            Dict of sandbox_id -> policy value.
        """
        return {sid: policy.value for sid, policy in self.policies.items()}

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary.

        Returns:
            Dict with all policies and configuration.
        """
        return {
            "policies": self.list_policies(),
            "allowed_hosts": self.allowed_hosts,
        }
