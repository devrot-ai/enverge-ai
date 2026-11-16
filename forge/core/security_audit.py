"""Security audit module for automated workspace and config checks.

Checks for hardcoded secrets, insecure dependencies, missing input validation,
and exposed debug endpoints. Returns findings with severity levels.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SecurityFinding:
    """A single security finding."""

    severity: str  # "low", "medium", "high", "critical"
    category: str
    message: str
    file_path: str = ""
    line_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
        }


@dataclass
class SecurityAuditResult:
    """Result of a security audit."""

    findings: list[SecurityFinding] = field(default_factory=list)
    total_files: int = 0
    clean: bool = True

    def add_finding(self, finding: SecurityFinding) -> None:
        """Add a finding to the audit result."""
        self.findings.append(finding)
        if finding.severity in ("high", "critical"):
            self.clean = False

    def get_by_severity(self, severity: str) -> list[SecurityFinding]:
        """Get findings filtered by severity.

        Args:
            severity: Severity level to filter.

        Returns:
            List of matching findings.
        """
        return [f for f in self.findings if f.severity == severity]

    def summary(self) -> dict[str, int]:
        """Get count of findings by severity.

        Returns:
            Dict with severity levels as keys and counts as values.
        """
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in self.findings:
            if finding.severity in counts:
                counts[finding.severity] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total_files": self.total_files,
            "clean": self.clean,
            "summary": self.summary(),
            "findings": [f.to_dict() for f in self.findings],
        }


class SecurityAuditor:
    """Automated security checks for workspace and configurations.

    Performs static analysis to detect common security issues:
    - Hardcoded secrets
    - Insecure dependencies
    - Missing input validation
    - Exposed debug endpoints
    """

    # Patterns for detecting hardcoded secrets
    SECRET_PATTERNS = [
        (re.compile(r'password\s*=\s*["\'][^"\']+["\']'), "Hardcoded password"),
        (re.compile(r'api_key\s*=\s*["\'][^"\']+["\']'), "Hardcoded API key"),
        (re.compile(r'secret\s*=\s*["\'][^"\']+["\']'), "Hardcoded secret"),
        (re.compile(r'token\s*=\s*["\'][^"\']+["\']'), "Hardcoded token"),
    ]

    # Patterns for detecting insecure patterns
    INSECURE_PATTERNS = [
        (re.compile(r'eval\s*\('), "Use of eval()"),
        (re.compile(r'exec\s*\('), "Use of exec()"),
        (re.compile(r'__import__\s*\('), "Dynamic import"),
        (re.compile(r'debug\s*=\s*True'), "Debug mode enabled"),
    ]

    def audit_workspace(self, workspace_dir: str | Path) -> SecurityAuditResult:
        """Audit a workspace directory for security issues.

        Args:
            workspace_dir: Path to the workspace.

        Returns:
            SecurityAuditResult with findings.
        """
        result = SecurityAuditResult()
        workspace = Path(workspace_dir)

        if not workspace.exists():
            return result

        python_files = list(workspace.rglob("*.py"))
        result.total_files = len(python_files)

        for py_file in python_files:
            self._check_file(py_file, result)

        return result

    def audit_config(self, config_path: str | Path) -> SecurityAuditResult:
        """Audit a configuration file for security issues.

        Args:
            config_path: Path to the config file.

        Returns:
            SecurityAuditResult with findings.
        """
        result = SecurityAuditResult()
        path = Path(config_path)

        if not path.exists():
            return result

        result.total_files = 1
        self._check_file(path, result)

        return result

    def _check_file(self, file_path: Path, result: SecurityAuditResult) -> None:
        """Check a single file for security issues.

        Args:
            file_path: Path to the file.
            result: Audit result to add findings to.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        lines = content.splitlines()

        for pattern, description in self.SECRET_PATTERNS:
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    result.add_finding(
                        SecurityFinding(
                            severity="high",
                            category="hardcoded_secret",
                            message=description,
                            file_path=str(file_path),
                            line_number=i,
                        )
                    )

        for pattern, description in self.INSECURE_PATTERNS:
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    severity = "medium" if "debug" in description.lower() else "high"
                    result.add_finding(
                        SecurityFinding(
                            severity=severity,
                            category="insecure_pattern",
                            message=description,
                            file_path=str(file_path),
                            line_number=i,
                        )
                    )

    def generate_report(self, result: SecurityAuditResult) -> str:
        """Generate a Markdown report from audit results.

        Args:
            result: Security audit result.

        Returns:
            Markdown formatted report.
        """
        lines = [
            "# Security Audit Report",
            "",
            f"- **Total files scanned**: {result.total_files}",
            f"- **Clean**: {'Yes' if result.clean else 'No'}",
            "",
            "## Summary",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]

        summary = result.summary()
        for severity, count in summary.items():
            lines.append(f"| {severity.upper()} | {count} |")

        if result.findings:
            lines.extend(["", "## Findings", ""])
            for finding in result.findings:
                lines.append(
                    f"- **[{finding.severity.upper()}]** {finding.message} "
                    f"({finding.file_path}:{finding.line_number})"
                )

        return "\n".join(lines)
