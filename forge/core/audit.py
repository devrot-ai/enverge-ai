"""Audit logging for ForgeLab actions.

Provides append-only JSONL audit logging for all significant actions
in the system. Includes timestamp, action, actor, target, outcome,
and duration.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: str
    action: str
    actor: str = ""
    target: str = ""
    outcome: str = ""
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "actor": self.actor,
            "target": self.target,
            "outcome": self.outcome,
            "duration_seconds": round(self.duration_seconds, 4),
            "details": self.details,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Append-only audit logger.

    Logs all significant actions to a JSONL file for reproducibility
    and debugging.
    """

    def __init__(self, log_dir: str | Path | None = None):
        """Initialize the audit logger.

        Args:
            log_dir: Directory for audit logs. Defaults to 'logs/'.
        """
        if log_dir is None:
            log_dir = "logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "audit.jsonl"

    def log(
        self,
        action: str,
        actor: str = "",
        target: str = "",
        outcome: str = "",
        duration_seconds: float = 0.0,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Log an action to the audit log.

        Args:
            action: Action name (e.g., "world_generate", "run_start").
            actor: Who performed the action (e.g., agent type, CLI).
            target: Target of the action (e.g., world_id, task_id).
            outcome: Result (e.g., "success", "failure").
            duration_seconds: How long the action took.
            details: Additional context.

        Returns:
            AuditEntry that was logged.
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            action=action,
            actor=actor,
            target=target,
            outcome=outcome,
            duration_seconds=duration_seconds,
            details=details or {},
        )

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry.to_json() + "\n")

        logger.debug(f"Audit: {action} by {actor} on {target} → {outcome}")
        return entry

    def read(
        self,
        action: str | None = None,
        since: str | None = None,
        limit: int | None = None,
    ) -> list[AuditEntry]:
        """Read audit log entries with optional filtering.

        Args:
            action: Filter by action name.
            since: Filter by timestamp (ISO format).
            limit: Maximum number of entries to return.

        Returns:
            List of audit entries matching the filters.
        """
        if not self.log_file.exists():
            return []

        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = AuditEntry(**data)
                except (json.JSONDecodeError, TypeError):
                    continue

                # Apply filters
                if action and entry.action != action:
                    continue
                if since and entry.timestamp < since:
                    continue

                entries.append(entry)

        # Return most recent first
        entries.reverse()

        if limit:
            entries = entries[:limit]

        return entries

    def count(self, action: str | None = None) -> int:
        """Count audit log entries.

        Args:
            action: If provided, count only entries with this action.

        Returns:
            Number of entries.
        """
        entries = self.read(action=action)
        return len(entries)

    def get_actions(self) -> list[str]:
        """Get list of unique action names in the log.

        Returns:
            Sorted list of unique action names.
        """
        entries = self.read()
        actions = set()
        for entry in entries:
            actions.add(entry.action)
        return sorted(actions)

    def clear(self) -> None:
        """Clear the audit log file."""
        if self.log_file.exists():
            self.log_file.unlink()
        logger.info("Audit log cleared")

    def rotate(self, max_size_mb: float = 10.0) -> None:
        """Rotate the audit log if it exceeds max size.

        Args:
            max_size_mb: Maximum file size in MB before rotation.
        """
        if not self.log_file.exists():
            return

        file_size_mb = self.log_file.stat().st_size / (1024 * 1024)
        if file_size_mb <= max_size_mb:
            return

        # Rotate: move current log to timestamped file
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rotated = self.log_dir / f"audit_{timestamp}.jsonl"
        self.log_file.rename(rotated)
        logger.info(f"Audit log rotated to {rotated} ({file_size_mb:.1f} MB)")
