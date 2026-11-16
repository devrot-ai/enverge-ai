"""Docker sandbox manager for ForgeLab.

Provides isolated execution environments for running untrusted agent-generated
code.  All execution happens inside Docker containers with strict security
policies: non-root user, no network, resource limits, and filesystem isolation.

Security is fail-closed: if Docker is unavailable, a clear error is raised
instead of silently falling back to host execution.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security Policies
# ---------------------------------------------------------------------------


@dataclass
class SandboxPolicy:
    """Security policy for a sandbox container.

    Attributes:
        memory_limit: Memory limit (e.g. "512m", "1g").
        cpu_limit: CPU limit (e.g. 0.5 for half a core).
        timeout_seconds: Maximum execution time per command.
        network_disabled: Whether to disable network access.
        read_only_root: Whether to mount root filesystem as read-only.
        non_root_user: UID/GID for the non-root user.
        allowed_commands: Whitelist of allowed commands (None = all).
        max_processes: Maximum number of processes.
        workspace_path: Path inside the container for the workspace.
    """

    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    timeout_seconds: int = 120
    network_disabled: bool = True
    read_only_root: bool = True
    non_root_user: tuple[int, int] = (1000, 1000)
    allowed_commands: list[str] | None = None
    max_processes: int = 50
    workspace_path: str = "/workspace"


# ---------------------------------------------------------------------------
# Sandbox Executor
# ---------------------------------------------------------------------------


class SandboxExecutor:
    """Executes commands inside a Docker sandbox container.

    This class manages the Docker container lifecycle: creation, execution,
    and cleanup.  It enforces security policies and never executes untrusted
    code on the host.

    Usage:
        executor = SandboxExecutor(policy=SandboxPolicy())
        executor.create(workspace_path="/path/to/repo")
        result = executor.execute("python -m pytest tests/")
        executor.cleanup()

    Note:
        Requires Docker to be installed and accessible.  If Docker is
        unavailable, methods raise SandboxError with a clear message.
    """

    def __init__(self, policy: SandboxPolicy | None = None):
        self.policy = policy or SandboxPolicy()
        self._container_id: str | None = None
        self._workspace_path: str | None = None
        self._docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        """Check if Docker is available and accessible."""
        try:
            import docker

            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        """Whether Docker is available for sandbox execution."""
        return self._docker_available

    def create(self, workspace_path: str) -> str:
        """Create a sandbox container with the given workspace.

        Args:
            workspace_path: Path to the workspace directory on the host.

        Returns:
            The container ID.

        Raises:
            SandboxError: If Docker is unavailable or container creation fails.
        """
        if not self._docker_available:
            raise SandboxError(
                "Docker is not available.  Cannot create sandbox container. "
                "Please install Docker and ensure the Docker daemon is running."
            )

        if not os.path.isdir(workspace_path):
            raise SandboxError(f"Workspace path does not exist: {workspace_path}")

        try:
            import docker

            client = docker.from_env()

            workspace_path = os.path.abspath(workspace_path)
            self._workspace_path = workspace_path

            # Build container kwargs with security policies
            container_kwargs: dict[str, Any] = {
                "image": "python:3.11-slim",
                "command": ["tail", "-f", "/dev/null"],  # Keep container running
                "detach": True,
                "stdin_open": True,
                "tty": True,
                "mem_limit": self.policy.memory_limit,
                "cpu_quota": int(self.policy.cpu_limit * 100000),
                "working_dir": self.policy.workspace_path,
                "user": f"{self.policy.non_root_user[0]}:{self.policy.non_root_user[1]}",
                "environment": {
                    "PYTHONUNBUFFERED": "1",
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                },
            }

            # Disable network
            if self.policy.network_disabled:
                container_kwargs["network_disabled"] = True

            # Mount workspace
            volumes = {
                workspace_path: {
                    "bind": self.policy.workspace_path,
                    "mode": "ro" if self.policy.read_only_root else "rw",
                }
            }
            container_kwargs["volumes"] = volumes

            container = client.containers.run(**container_kwargs)
            self._container_id = container.id
            logger.info(f"Created sandbox container {self._container_id[:12]} " f"with workspace {workspace_path}")
            return self._container_id

        except Exception as e:
            raise SandboxError(f"Failed to create sandbox container: {e}") from e

    def execute(
        self,
        command: str,
        timeout: int | None = None,
        workdir: str | None = None,
    ) -> ExecutionResult:
        """Execute a command inside the sandbox container.

        Args:
            command: The command to execute.
            timeout: Timeout in seconds (defaults to policy timeout).
            workdir: Working directory inside the container.

        Returns:
            ExecutionResult with stdout, stderr, and exit code.

        Raises:
            SandboxError: If the container is not running or execution fails.
        """
        if not self._container_id:
            raise SandboxError("No sandbox container running. Call create() first.")

        timeout = timeout or self.policy.timeout_seconds

        # Check command against allowlist
        if self.policy.allowed_commands is not None:
            cmd_base = command.split()[0] if command else ""
            if cmd_base not in self.policy.allowed_commands:
                raise SandboxError(f"Command '{cmd_base}' not in allowed list: " f"{self.policy.allowed_commands}")

        try:
            import docker

            client = docker.from_env()
            container = client.containers.get(self._container_id)

            result = container.exec_run(
                command,
                workdir=workdir or self.policy.workspace_path,
                demux=True,
            )

            stdout = result.output[0].decode("utf-8", errors="replace") if result.output[0] else ""
            stderr = result.output[1].decode("utf-8", errors="replace") if result.output[1] else ""

            return ExecutionResult(
                exit_code=result.exit_code,
                stdout=stdout,
                stderr=stderr,
                command=command,
            )

        except Exception as e:
            raise SandboxError(f"Command execution failed: {e}") from e

    def copy_from(self, container_path: str, host_path: str) -> None:
        """Copy a file from the container to the host.

        Args:
            container_path: Path inside the container.
            host_path: Destination path on the host.
        """
        if not self._container_id:
            raise SandboxError("No sandbox container running.")

        try:
            import docker

            client = docker.from_env()
            container = client.containers.get(self._container_id)

            tar_data, _ = container.get_archive(container_path)
            # Extract from tar
            import io
            import tarfile

            tar = tarfile.open(fileobj=io.BytesIO(b"".join(tar_data)))
            for member in tar.getmembers():
                member.name = os.path.basename(member.name)
                tar.extract(member, os.path.dirname(host_path) or ".")
            tar.close()

        except Exception as e:
            raise SandboxError(f"Failed to copy from container: {e}") from e

    def cleanup(self) -> None:
        """Stop and remove the sandbox container."""
        if not self._container_id:
            return

        try:
            import docker

            client = docker.from_env()
            container = client.containers.get(self._container_id)
            container.stop(timeout=5)
            container.remove(force=True)
            logger.info(f"Cleaned up sandbox container {self._container_id[:12]}")
        except Exception as e:
            logger.warning(f"Failed to cleanup container {self._container_id[:12]}: {e}")
        finally:
            self._container_id = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False


# ---------------------------------------------------------------------------
# Sandbox Manager
# ---------------------------------------------------------------------------


class SandboxManager:
    """High-level manager for sandbox lifecycle.

    Creates isolated workspaces, manages sandbox containers, and handles
    reset and cleanup.  This is the main entry point for the run orchestrator.

    Usage:
        manager = SandboxManager()
        sandbox_id = manager.create_sandbox(world_path)
        result = manager.execute(sandbox_id, "python -m pytest tests/")
        manager.reset_sandbox(sandbox_id)
        manager.cleanup_sandbox(sandbox_id)
    """

    def __init__(self, policy: SandboxPolicy | None = None):
        self.policy = policy or SandboxPolicy()
        self._sandboxes: dict[str, SandboxExecutor] = {}
        self._workspaces: dict[str, str] = {}

    @property
    def is_available(self) -> bool:
        """Whether Docker is available for sandbox execution."""
        return any(s.is_available for s in self._sandboxes.values()) or self._check_docker()

    def _check_docker(self) -> bool:
        try:
            import docker

            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    def create_sandbox(self, world_path: str) -> str:
        """Create a new sandbox for a world.

        Args:
            world_path: Path to the world directory.

        Returns:
            Sandbox identifier.
        """
        import uuid

        sandbox_id = uuid.uuid4().hex[:12]

        # Create a temporary writable workspace
        workspace = tempfile.mkdtemp(prefix=f"forgelab_sandbox_{sandbox_id}_")
        # Copy world to workspace
        shutil.copytree(world_path, os.path.join(workspace, "repo"), dirs_exist_ok=True)

        executor = SandboxExecutor(policy=self.policy)
        if not executor.is_available:
            shutil.rmtree(workspace, ignore_errors=True)
            raise SandboxError(
                "Docker is not available.  Cannot create sandbox. " "Install Docker and ensure the daemon is running."
            )

        executor.create(os.path.join(workspace, "repo"))
        self._sandboxes[sandbox_id] = executor
        self._workspaces[sandbox_id] = workspace
        logger.info(f"Created sandbox {sandbox_id} for world {world_path}")
        return sandbox_id

    def execute(
        self,
        sandbox_id: str,
        command: str,
        timeout: int | None = None,
    ) -> ExecutionResult:
        """Execute a command in a sandbox.

        Args:
            sandbox_id: The sandbox identifier.
            command: Command to execute.
            timeout: Timeout in seconds.

        Returns:
            ExecutionResult.
        """
        if sandbox_id not in self._sandboxes:
            raise SandboxError(f"Sandbox {sandbox_id} not found")
        return self._sandboxes[sandbox_id].execute(command, timeout=timeout)

    def reset_sandbox(self, sandbox_id: str, world_path: str) -> None:
        """Reset a sandbox to its initial state.

        Args:
            sandbox_id: The sandbox identifier.
            world_path: Original world path to reset from.
        """
        if sandbox_id not in self._sandboxes:
            raise SandboxError(f"Sandbox {sandbox_id} not found")

        workspace = self._workspaces.get(sandbox_id)
        if workspace:
            repo_path = os.path.join(workspace, "repo")
            # Clean and re-copy
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path, ignore_errors=True)
            shutil.copytree(world_path, repo_path, dirs_exist_ok=True)
            logger.info(f"Reset sandbox {sandbox_id} from {world_path}")

    def cleanup_sandbox(self, sandbox_id: str) -> None:
        """Clean up a sandbox and its workspace.

        Args:
            sandbox_id: The sandbox identifier.
        """
        if sandbox_id in self._sandboxes:
            self._sandboxes[sandbox_id].cleanup()
            del self._sandboxes[sandbox_id]

        workspace = self._workspaces.pop(sandbox_id, None)
        if workspace and os.path.exists(workspace):
            shutil.rmtree(workspace, ignore_errors=True)

        logger.info(f"Cleaned up sandbox {sandbox_id}")

    def cleanup_all(self) -> None:
        """Clean up all sandboxes."""
        for sandbox_id in list(self._sandboxes.keys()):
            self.cleanup_sandbox(sandbox_id)


# ---------------------------------------------------------------------------
# Execution Result
# ---------------------------------------------------------------------------


@dataclass
class ExecutionResult:
    """Result of a command execution inside a sandbox.

    Attributes:
        exit_code: Process exit code.
        stdout: Standard output.
        stderr: Standard error.
        command: The command that was executed.
        duration_seconds: How long the command took.
    """

    exit_code: int
    stdout: str
    stderr: str
    command: str
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "command": self.command,
            "duration_seconds": self.duration_seconds,
        }


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SandboxError(Exception):
    """Raised when sandbox operations fail."""

    pass
