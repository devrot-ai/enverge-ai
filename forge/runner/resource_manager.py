"""Resource-aware scheduling for parallel execution.

Monitors CPU and memory usage to limit parallel workers based on
available system resources. Integrates with TaskQueue for pause/resume.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ResourceUsage:
    """Current system resource usage."""

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    active_workers: int = 0


class ResourceManager:
    """Manages system resources for parallel task execution.

    Monitors CPU and memory usage via psutil (optional) and limits
    parallel workers based on available resources.
    """

    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        max_memory_percent: float = 70.0,
        max_workers: int = 4,
    ):
        """Initialize the resource manager.

        Args:
            max_cpu_percent: Maximum CPU usage before pausing (default 80%).
            max_memory_percent: Maximum memory usage before pausing (default 70%).
            max_workers: Maximum number of parallel workers (default 4).
        """
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_workers = max_workers
        self.active_workers = 0
        self._psutil = None
        try:
            import psutil
            self._psutil = psutil
        except ImportError:
            logger.info("psutil not installed; resource manager will use no limits")

    def check_available(self) -> bool:
        """Check if resources are available for a new worker.

        Returns:
            True if resources are available, False otherwise.
        """
        if self.active_workers >= self.max_workers:
            return False

        usage = self.get_utilization()
        if usage.cpu_percent >= self.max_cpu_percent:
            return False
        if usage.memory_percent >= self.max_memory_percent:
            return False

        return True

    def allocate(self) -> bool:
        """Allocate a worker slot.

        Returns:
            True if allocation succeeded, False if resources exhausted.
        """
        if not self.check_available():
            return False
        self.active_workers += 1
        logger.debug(f"Allocated worker {self.active_workers}")
        return True

    def release(self) -> None:
        """Release a worker slot."""
        if self.active_workers > 0:
            self.active_workers -= 1
            logger.debug(f"Released worker, remaining: {self.active_workers}")

    def get_utilization(self) -> ResourceUsage:
        """Get current resource utilization.

        Returns:
            ResourceUsage with current CPU, memory, and worker counts.
        """
        cpu = 0.0
        memory = 0.0

        if self._psutil is not None:
            cpu = self._psutil.cpu_percent(interval=0.1)
            mem = self._psutil.virtual_memory()
            memory = mem.percent

        return ResourceUsage(
            cpu_percent=cpu,
            memory_percent=memory,
            active_workers=self.active_workers,
        )

    def should_pause(self) -> bool:
        """Check if execution should be paused due to resource pressure.

        Returns:
            True if resources are exhausted and workers should be paused.
        """
        usage = self.get_utilization()
        return (
            usage.cpu_percent >= self.max_cpu_percent
            or usage.memory_percent >= self.max_memory_percent
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary.

        Returns:
            Dict representation.
        """
        usage = self.get_utilization()
        return {
            "max_cpu_percent": self.max_cpu_percent,
            "max_memory_percent": self.max_memory_percent,
            "max_workers": self.max_workers,
            "active_workers": self.active_workers,
            "cpu_percent": usage.cpu_percent,
            "memory_percent": usage.memory_percent,
            "psutil_available": self._psutil is not None,
        }
