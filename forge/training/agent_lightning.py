"""Microsoft Agent Lightning integration for ForgeLab.

Connects to Microsoft's Agent Lightning framework for distributed agent
training and evaluation. Provides an interface for running ForgeLab
experiments through the Agent Lightning pipeline.

Configuration via environment variables:
    AGENT_LIGHTNING_ENDPOINT - Agent Lightning server URL
    AGENT_LIGHTNING_API_KEY - API key for authentication
    AGENT_LIGHTNING_WORKSPACE - Workspace name

Requires: pip install agent-lightning (when available)
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentLightningConfig:
    """Configuration for Agent Lightning integration."""

    endpoint: str = "http://localhost:8080"
    api_key: str = ""
    workspace: str = "forgelab"
    max_concurrent_runs: int = 4
    timeout: int = 3600


@dataclass
class LightningRun:
    """A run submitted to Agent Lightning."""

    run_id: str
    task_id: str
    agent_type: str
    status: str = "pending"
    result: dict[str, Any] = field(default_factory=dict)
    submitted_at: float = 0.0
    completed_at: float = 0.0


class AgentLightningClient:
    """Client for Microsoft Agent Lightning integration.

    Submits ForgeLab tasks to Agent Lightning for distributed execution
    and collects results. Falls back gracefully if not available.
    """

    def __init__(self, config: AgentLightningConfig | None = None):
        self.config = config or AgentLightningConfig()
        self._available = False
        self._runs: dict[str, LightningRun] = {}

        # Check availability
        api_key = os.environ.get(
            "AGENT_LIGHTNING_API_KEY", self.config.api_key
        )
        if not api_key:
            logger.warning(
                "Agent Lightning API key not set. "
                "Set AGENT_LIGHTNING_API_KEY environment variable."
            )
            return

        try:
            import urllib.request

            endpoint = os.environ.get(
                "AGENT_LIGHTNING_ENDPOINT", self.config.endpoint
            )
            req = urllib.request.Request(
                f"{endpoint}/health", method="GET"
            )
            req.add_header("Authorization", f"Bearer {api_key}")
            urllib.request.urlopen(req, timeout=10)
            self._available = True
            logger.info("Agent Lightning client connected to %s", endpoint)
        except Exception as e:
            logger.warning(
                "Agent Lightning not reachable: %s. "
                "Will fall back to local execution.", e
            )

    def submit_task(
        self,
        task_id: str,
        agent_type: str,
        task_spec: dict[str, Any],
        workspace_dir: str,
    ) -> LightningRun | None:
        """Submit a task to Agent Lightning.

        Args:
            task_id: Task identifier.
            agent_type: Agent type to use.
            task_spec: Task specification dictionary.
            workspace_dir: Path to workspace directory.

        Returns:
            LightningRun object or None if unavailable.
        """
        if not self._available:
            logger.warning(
                "Agent Lightning not available. Task %s will run locally.",
                task_id,
            )
            return None

        run_id = f"al-{uuid.uuid4().hex[:12]}"
        run = LightningRun(
            run_id=run_id,
            task_id=task_id,
            agent_type=agent_type,
            status="submitted",
            submitted_at=time.time(),
        )

        try:
            import urllib.request

            payload = json.dumps(
                {
                    "run_id": run_id,
                    "task_id": task_id,
                    "agent_type": agent_type,
                    "task_spec": task_spec,
                    "workspace_dir": workspace_dir,
                }
            ).encode()

            endpoint = os.environ.get(
                "AGENT_LIGHTNING_ENDPOINT", self.config.endpoint
            )
            api_key = os.environ.get(
                "AGENT_LIGHTNING_API_KEY", self.config.api_key
            )

            req = urllib.request.Request(
                f"{endpoint}/v1/runs",
                data=payload,
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {api_key}")

            response = urllib.request.urlopen(req, timeout=30)
            result = json.loads(response.read().decode())

            run.status = result.get("status", "submitted")
            self._runs[run_id] = run

            logger.info("Task %s submitted to Agent Lightning as %s", task_id, run_id)
            return run

        except Exception as e:
            logger.error("Failed to submit task to Agent Lightning: %s", e)
            run.status = "failed"
            return None

    def get_run_status(self, run_id: str) -> dict[str, Any] | None:
        """Get the status of a submitted run.

        Args:
            run_id: Run identifier.

        Returns:
            Status dictionary or None.
        """
        if not self._available:
            return None

        try:
            import urllib.request

            endpoint = os.environ.get(
                "AGENT_LIGHTNING_ENDPOINT", self.config.endpoint
            )
            api_key = os.environ.get(
                "AGENT_LIGHTNING_API_KEY", self.config.api_key
            )

            req = urllib.request.Request(
                f"{endpoint}/v1/runs/{run_id}/status",
                method="GET",
            )
            req.add_header("Authorization", f"Bearer {api_key}")

            response = urllib.request.urlopen(req, timeout=10)
            result = json.loads(response.read().decode())

            if run_id in self._runs:
                self._runs[run_id].status = result.get("status", "unknown")

            return result

        except Exception as e:
            logger.error("Failed to get run status: %s", e)
            return None

    def get_run_result(self, run_id: str) -> dict[str, Any] | None:
        """Get the result of a completed run.

        Args:
            run_id: Run identifier.

        Returns:
            Result dictionary or None.
        """
        if not self._available:
            return None

        try:
            import urllib.request

            endpoint = os.environ.get(
                "AGENT_LIGHTNING_ENDPOINT", self.config.endpoint
            )
            api_key = os.environ.get(
                "AGENT_LIGHTNING_API_KEY", self.config.api_key
            )

            req = urllib.request.Request(
                f"{endpoint}/v1/runs/{run_id}/result",
                method="GET",
            )
            req.add_header("Authorization", f"Bearer {api_key}")

            response = urllib.request.urlopen(req, timeout=30)
            result = json.loads(response.read().decode())

            if run_id in self._runs:
                self._runs[run_id].result = result
                self._runs[run_id].completed_at = time.time()

            return result

        except Exception as e:
            logger.error("Failed to get run result: %s", e)
            return None

    def cancel_run(self, run_id: str) -> bool:
        """Cancel a running task.

        Args:
            run_id: Run identifier.

        Returns:
            True if cancelled successfully.
        """
        if not self._available:
            return False

        try:
            import urllib.request

            endpoint = os.environ.get(
                "AGENT_LIGHTNING_ENDPOINT", self.config.endpoint
            )
            api_key = os.environ.get(
                "AGENT_LIGHTNING_API_KEY", self.config.api_key
            )

            req = urllib.request.Request(
                f"{endpoint}/v1/runs/{run_id}/cancel",
                method="POST",
            )
            req.add_header("Authorization", f"Bearer {api_key}")

            urllib.request.urlopen(req, timeout=10)

            if run_id in self._runs:
                self._runs[run_id].status = "cancelled"

            return True

        except Exception as e:
            logger.error("Failed to cancel run: %s", e)
            return False

    def list_runs(self) -> list[LightningRun]:
        """List all submitted runs.

        Returns:
            List of LightningRun objects.
        """
        return list(self._runs.values())

    def get_status(self) -> dict[str, Any]:
        """Get client status."""
        return {
            "available": self._available,
            "config": {
                "endpoint": self.config.endpoint,
                "workspace": self.config.workspace,
            },
            "runs_submitted": len(self._runs),
        }
