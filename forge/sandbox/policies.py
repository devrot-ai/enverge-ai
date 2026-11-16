"""Docker sandbox security policies.

Defines security policies for Docker container execution,
including resource limits, network restrictions, and capability dropping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SandboxPolicy:
    """Security policy for a Docker sandbox container.

    Attributes:
        memory_limit: Memory limit (e.g. "512m", "1g").
        cpu_limit: CPU limit (e.g. "0.5", "1.0").
        network_disabled: Whether to disable network access.
        read_only_rootfs: Whether to use read-only root filesystem.
        non_root_user: Whether to run as non-root user.
        no_new_privileges: Whether to prevent privilege escalation.
        dropped_capabilities: List of Linux capabilities to drop.
        process_limit: Maximum number of processes.
        tmpfs_size: Size of /tmp mount.
    """

    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    network_disabled: bool = True
    read_only_rootfs: bool = True
    non_root_user: bool = True
    no_new_privileges: bool = True
    dropped_capabilities: list[str] = field(default_factory=lambda: ["ALL"])
    process_limit: int = 100
    tmpfs_size: str = "128m"

    def to_docker_args(self) -> list[str]:
        """Convert policy to Docker run arguments.

        Returns:
            List of Docker CLI arguments.
        """
        args = []

        # Resource limits
        args.extend(["--memory", self.memory_limit])
        args.extend(["--cpus", self.cpu_limit])

        # Network
        if self.network_disabled:
            args.append("--network=none")

        # Filesystem
        if self.read_only_rootfs:
            args.append("--read-only")

        # User
        if self.non_root_user:
            args.extend(["--user", "1000:1000"])

        # Security
        if self.no_new_privileges:
            args.append("--security-opt=no-new-privileges:true")

        # Capabilities
        for cap in self.dropped_capabilities:
            args.extend(["--cap-drop", cap])

        # Process limit
        args.extend(["--pids-limit", str(self.process_limit)])

        # Tmpfs
        args.extend(["--tmpfs", f"/tmp:size={self.tmpfs_size}"])

        return args

    def to_dict(self) -> dict[str, Any]:
        """Export policy as dictionary.

        Returns:
            Dictionary with policy settings.
        """
        return {
            "memory_limit": self.memory_limit,
            "cpu_limit": self.cpu_limit,
            "network_disabled": self.network_disabled,
            "read_only_rootfs": self.read_only_rootfs,
            "non_root_user": self.non_root_user,
            "no_new_privileges": self.no_new_privileges,
            "dropped_capabilities": self.dropped_capabilities,
            "process_limit": self.process_limit,
            "tmpfs_size": self.tmpfs_size,
        }


def get_default_policy() -> SandboxPolicy:
    """Get the default sandbox security policy.

    Returns:
        Default SandboxPolicy instance.
    """
    return SandboxPolicy()


def get_relaxed_policy() -> SandboxPolicy:
    """Get a relaxed policy for development/testing.

    Returns:
        Relaxed SandboxPolicy instance.
    """
    return SandboxPolicy(
        memory_limit="1g",
        cpu_limit="2.0",
        network_disabled=False,
        read_only_rootfs=False,
        process_limit=200,
    )


def get_strict_policy() -> SandboxPolicy:
    """Get a strict policy for production use.

    Returns:
        Strict SandboxPolicy instance.
    """
    return SandboxPolicy(
        memory_limit="256m",
        cpu_limit="0.5",
        network_disabled=True,
        read_only_rootfs=True,
        non_root_user=True,
        no_new_privileges=True,
        dropped_capabilities=["ALL"],
        process_limit=50,
        tmpfs_size="64m",
    )
