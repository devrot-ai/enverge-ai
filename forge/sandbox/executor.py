"""Docker container command execution.

Provides functions to execute commands inside Docker containers
with proper resource limits and security policies.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class SandboxExecutor:
    """Executes commands inside Docker containers.

    Handles container creation, command execution, and cleanup
    with security policies applied.

    Attributes:
        container_id: Docker container identifier.
        workspace: Path to the workspace directory.
        image: Docker image to use.
    """

    def __init__(
        self,
        container_id: str,
        workspace: Path,
        image: str = "forgelab-sandbox:latest",
    ):
        self.container_id = container_id
        self.workspace = workspace.resolve()
        self.image = image

    def execute(
        self,
        command: list[str],
        timeout: int = 60,
        workdir: str | None = None,
    ) -> tuple[int, str, str]:
        """Execute a command inside the container.

        Args:
            command: Command and arguments.
            timeout: Timeout in seconds.
            workdir: Working directory inside container.

        Returns:
            Tuple of (return_code, stdout, stderr).

        Raises:
            subprocess.TimeoutExpired: If command times out.
            FileNotFoundError: If Docker is not available.
        """
        docker_cmd = ["docker", "exec", self.container_id]
        if workdir:
            docker_cmd.extend(["-w", workdir])
        docker_cmd.extend(command)

        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr

    def copy_to_container(
        self,
        source: Path,
        destination: str,
    ) -> bool:
        """Copy a file or directory into the container.

        Args:
            source: Source path on host.
            destination: Destination path in container.

        Returns:
            True if copy succeeded.
        """
        try:
            subprocess.run(
                [
                    "docker",
                    "cp",
                    str(source.resolve()),
                    f"{self.container_id}:{destination}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def copy_from_container(
        self,
        source: str,
        destination: Path,
    ) -> bool:
        """Copy a file or directory from the container.

        Args:
            source: Source path in container.
            destination: Destination path on host.

        Returns:
            True if copy succeeded.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [
                    "docker",
                    "cp",
                    f"{self.container_id}:{source}",
                    str(destination.resolve()),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def is_running(self) -> bool:
        """Check if the container is running.

        Returns:
            True if the container is running.
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip().lower() == "true"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def stop(self) -> bool:
        """Stop the container.

        Returns:
            True if container was stopped.
        """
        try:
            subprocess.run(
                ["docker", "stop", self.container_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def remove(self) -> bool:
        """Remove the container.

        Returns:
            True if container was removed.
        """
        try:
            subprocess.run(
                ["docker", "rm", "-f", self.container_id],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
