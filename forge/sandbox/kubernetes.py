"""Kubernetes-based sandbox orchestration for ForgeLab.

Manages sandbox containers on Kubernetes clusters for distributed,
scalable agent execution. Falls back to Docker when K8s is unavailable.

Configuration via environment variables:
    KUBE_CONFIG - Path to Kubernetes config file
    KUBE_NAMESPACE - Kubernetes namespace (default: forgelab)
    KUBE_IMAGE - Sandbox container image

Requires: pip install kubernetes
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class K8SConfig:
    """Configuration for Kubernetes sandbox."""

    namespace: str = "forgelab"
    image: str = "forgelab/sandbox:latest"
    cpu_limit: str = "1000m"
    memory_limit: str = "512Mi"
    cpu_request: str = "500m"
    memory_request: str = "256Mi"
    timeout: int = 300
    replicas: int = 1
    service_account: str = "forgelab-sandbox"


@dataclass
class K8SSandbox:
    """A sandbox pod on Kubernetes."""

    sandbox_id: str
    pod_name: str
    namespace: str
    status: str = "pending"
    logs: str = ""
    created_at: float = 0.0
    completed_at: float = 0.0


class K8SSandboxManager:
    """Kubernetes-based sandbox orchestration.

    Creates and manages sandbox pods on Kubernetes for isolated agent
    execution. Falls back gracefully if K8s is not available.
    """

    def __init__(self, config: K8SConfig | None = None):
        self.config = config or K8SConfig()
        self._available = False
        self._client = None
        self._sandboxes: dict[str, K8SSandbox] = {}

        try:
            from kubernetes import client, config  # noqa: F401

            # Try in-cluster config first, then kubeconfig
            kube_config = os.environ.get("KUBE_CONFIG")
            if kube_config:
                config.load_kube_config(config_file=kube_config)
            else:
                try:
                    config.load_incluster_config()
                except Exception:
                    config.load_kube_config()

            self._client = client.CoreV1Api()
            self._batch_client = client.BatchV1Api()
            self._available = True

            namespace = os.environ.get("KUBE_NAMESPACE", self.config.namespace)
            logger.info(
                "K8s sandbox manager connected to namespace %s", namespace
            )
        except Exception as e:
            logger.warning(
                "Kubernetes not available: %s. "
                "Falling back to Docker sandbox.", e
            )

    def create_sandbox(
        self, workspace_dir: str, task_id: str
    ) -> K8SSandbox | None:
        """Create a sandbox pod on Kubernetes.

        Args:
            workspace_dir: Path to workspace directory.
            task_id: Task identifier.

        Returns:
            K8SSandbox object or None if unavailable.
        """
        if not self._available:
            logger.warning(
                "K8s not available. Using local sandbox for task %s.", task_id
            )
            return None

        sandbox_id = f"sb-{uuid.uuid4().hex[:12]}"
        pod_name = f"sandbox-{sandbox_id}"
        namespace = os.environ.get("KUBE_NAMESPACE", self.config.namespace)

        sandbox = K8SSandbox(
            sandbox_id=sandbox_id,
            pod_name=pod_name,
            namespace=namespace,
            status="creating",
            created_at=time.time(),
        )

        try:
            from kubernetes import client, utils

            # Create pod spec
            pod_spec = client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="sandbox",
                        image=os.environ.get(
                            "KUBE_IMAGE", self.config.image
                        ),
                        command=["python", "-m", "pytest", "/workspace/tests/"],
                        volume_mounts=[
                            client.V1VolumeMount(
                                name="workspace",
                                mount_path="/workspace",
                            )
                        ],
                        resources=client.V1ResourceRequirements(
                            limits={
                                "cpu": self.config.cpu_limit,
                                "memory": self.config.memory_limit,
                            },
                            requests={
                                "cpu": self.config.cpu_request,
                                "memory": self.config.memory_request,
                            },
                        ),
                        env=[
                            client.V1EnvVar(
                                name="TASK_ID", value=task_id
                            ),
                            client.V1EnvVar(
                                name="SANDBOX_ID", value=sandbox_id
                            ),
                        ],
                    )
                ],
                volumes=[
                    client.V1Volume(
                        name="workspace",
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=f"workspace-{task_id}"
                        ),
                    )
                ],
                restart_policy="Never",
                active_deadline_seconds=self.config.timeout,
            )

            pod = client.V1Pod(
                api_version="v1",
                kind="Pod",
                metadata=client.V1ObjectMeta(
                    name=pod_name,
                    namespace=namespace,
                    labels={
                        "app": "forgelab",
                        "sandbox-id": sandbox_id,
                        "task-id": task_id,
                    },
                ),
                spec=pod_spec,
            )

            self._client.create_namespaced_pod(namespace, pod)
            sandbox.status = "running"
            self._sandboxes[sandbox_id] = sandbox

            logger.info(
                "Created K8s sandbox %s (pod: %s/%s)",
                sandbox_id,
                namespace,
                pod_name,
            )
            return sandbox

        except Exception as e:
            logger.error("Failed to create K8s sandbox: %s", e)
            sandbox.status = "failed"
            return None

    def get_sandbox_status(self, sandbox_id: str) -> str | None:
        """Get the status of a sandbox pod.

        Args:
            sandbox_id: Sandbox identifier.

        Returns:
            Status string or None.
        """
        if not self._available or sandbox_id not in self._sandboxes:
            return None

        sandbox = self._sandboxes[sandbox_id]
        try:
            pod = self._client.read_namespaced_pod(
                sandbox.pod_name, sandbox.namespace
            )
            status = pod.status.phase
            sandbox.status = status.lower()

            if status in ("Succeeded", "Failed"):
                sandbox.completed_at = time.time()

            return status.lower()

        except Exception as e:
            logger.error("Failed to get sandbox status: %s", e)
            return None

    def get_sandbox_logs(self, sandbox_id: str) -> str | None:
        """Get logs from a sandbox pod.

        Args:
            sandbox_id: Sandbox identifier.

        Returns:
            Log string or None.
        """
        if not self._available or sandbox_id not in self._sandboxes:
            return None

        sandbox = self._sandboxes[sandbox_id]
        try:
            logs = self._client.read_namespaced_pod_log(
                sandbox.pod_name, sandbox.namespace
            )
            sandbox.logs = logs
            return logs

        except Exception as e:
            logger.error("Failed to get sandbox logs: %s", e)
            return None

    def delete_sandbox(self, sandbox_id: str) -> bool:
        """Delete a sandbox pod.

        Args:
            sandbox_id: Sandbox identifier.

        Returns:
            True if deleted successfully.
        """
        if not self._available or sandbox_id not in self._sandboxes:
            return False

        sandbox = self._sandboxes[sandbox_id]
        try:
            self._client.delete_namespaced_pod(
                sandbox.pod_name, sandbox.namespace
            )
            sandbox.status = "deleted"
            logger.info("Deleted K8s sandbox %s", sandbox_id)
            return True

        except Exception as e:
            logger.error("Failed to delete sandbox: %s", e)
            return False

    def list_sandboxes(self) -> list[K8SSandbox]:
        """List all active sandboxes.

        Returns:
            List of K8SSandbox objects.
        """
        return list(self._sandboxes.values())

    def create_job(
        self, task_id: str, agent_type: str, command: list[str]
    ) -> str | None:
        """Create a Kubernetes Job for agent execution.

        Args:
            task_id: Task identifier.
            agent_type: Agent type.
            command: Command to run.

        Returns:
            Job name or None.
        """
        if not self._available:
            return None

        try:
            from kubernetes import client

            namespace = os.environ.get("KUBE_NAMESPACE", self.config.namespace)
            job_name = f"agent-{task_id}-{uuid.uuid4().hex[:8]}"

            job_spec = client.V1JobSpec(
                template=client.V1PodTemplateSpec(
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
                                name="agent",
                                image=os.environ.get(
                                    "KUBE_IMAGE", self.config.image
                                ),
                                command=command,
                                env=[
                                    client.V1EnvVar(
                                        name="TASK_ID", value=task_id
                                    ),
                                    client.V1EnvVar(
                                        name="AGENT_TYPE", value=agent_type
                                    ),
                                ],
                            )
                        ],
                        restart_policy="Never",
                    )
                ),
                ttl_after_finished=300,
            )

            job = client.V1Job(
                api_version="batch/v1",
                kind="Job",
                metadata=client.V1ObjectMeta(
                    name=job_name,
                    namespace=namespace,
                    labels={
                        "app": "forgelab",
                        "task-id": task_id,
                    },
                ),
                spec=job_spec,
            )

            self._batch_client.create_namespaced_job(namespace, job)
            logger.info("Created K8s job %s", job_name)
            return job_name

        except Exception as e:
            logger.error("Failed to create K8s job: %s", e)
            return None

    def get_status(self) -> dict[str, Any]:
        """Get manager status."""
        return {
            "available": self._available,
            "config": {
                "namespace": self.config.namespace,
                "image": self.config.image,
            },
            "active_sandboxes": len(
                [
                    s
                    for s in self._sandboxes.values()
                    if s.status == "running"
                ]
            ),
        }
