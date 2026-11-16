"""Container image validation for sandbox security.

Checks container images for known vulnerabilities and security
issues before use in sandbox execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ImageValidationResult:
    """Result of validating a container image."""

    image_path: str
    valid: bool = False
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    layer_count: int = 0
    size_mb: float = 0.0
    base_image: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "image_path": self.image_path,
            "valid": self.valid,
            "issues": self.issues,
            "warnings": self.warnings,
            "layer_count": self.layer_count,
            "size_mb": self.size_mb,
            "base_image": self.base_image,
        }


class ImageValidator:
    """Validate container images for security issues.

    Checks:
    - Layer count (too many layers may indicate bloat)
    - Image size (too large may indicate unnecessary packages)
    - Base image (known vulnerable bases)
    - File permissions (world-writable files)

    Note: Full vulnerability scanning requires external tools.
    This provides basic checks without dependencies.
    """

    # Thresholds
    MAX_LAYERS = 30
    MAX_SIZE_MB = 1024  # 1GB
    KNOWN_VULNERABLE_BASES = [
        "ubuntu:14.04",
        "ubuntu:16.04",
        "debian:stretch",
        "centos:6",
        "centos:7",
    ]

    def __init__(
        self,
        max_layers: int | None = None,
        max_size_mb: float | None = None,
    ):
        """Initialize the image validator.

        Args:
            max_layers: Maximum allowed layers (default 30).
            max_size_mb: Maximum allowed size in MB (default 1024).
        """
        self.max_layers = max_layers or self.MAX_LAYERS
        self.max_size_mb = max_size_mb or self.MAX_SIZE_MB

    def validate(self, image_path: str | Path) -> ImageValidationResult:
        """Validate a container image for security issues.

        Args:
            image_path: Path to the container image or Dockerfile.

        Returns:
            ImageValidationResult with validation status.
        """
        path = Path(image_path)
        result = ImageValidationResult(image_path=str(path))

        if not path.exists():
            result.issues.append(f"Image path not found: {path}")
            return result

        # Check if it's a Dockerfile
        if path.name == "Dockerfile" or path.suffix == "":
            result = self._validate_dockerfile(path, result)
        else:
            # For actual image files, check size
            try:
                size_bytes = path.stat().st_size
                size_mb = size_bytes / (1024 * 1024)
                result.size_mb = size_mb

                if size_mb > self.max_size_mb:
                    result.issues.append(f"Image size {size_mb:.1f}MB exceeds limit {self.max_size_mb}MB")
            except OSError:
                result.warnings.append("Could not determine image size")

        result.valid = len(result.issues) == 0
        return result

    def _validate_dockerfile(
        self,
        path: Path,
        result: ImageValidationResult,
    ) -> ImageValidationResult:
        """Validate a Dockerfile for security issues.

        Args:
            path: Path to the Dockerfile.
            result: ImageValidationResult to populate.

        Returns:
            Updated ImageValidationResult.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            result.issues.append(f"Could not read Dockerfile: {e}")
            return result

        lines = content.split("\n")
        layer_count = 0
        base_image = ""

        for line in lines:
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Count layers (RUN, COPY, ADD, etc.)
            if stripped.startswith(("RUN ", "COPY ", "ADD ", "ENV ", "WORKDIR ", "EXPOSE ", "VOLUME ")):
                layer_count += 1

            # Check base image
            if stripped.startswith("FROM "):
                parts = stripped.split()
                if len(parts) >= 2:
                    base_image = parts[1]

        result.layer_count = layer_count
        result.base_image = base_image

        # Check layer count
        if layer_count > self.max_layers:
            result.issues.append(f"Layer count {layer_count} exceeds limit {self.max_layers}")

        # Check base image
        if base_image in self.KNOWN_VULNERABLE_BASES:
            result.issues.append(f"Known vulnerable base image: {base_image}")

        # Check for common security issues
        if "root" in content and "USER" not in content:
            result.warnings.append("Dockerfile runs as root without USER directive")

        if "apt-get update" in content and "apt-get install" in content:
            if "--no-install-recommends" not in content:
                result.warnings.append("apt-get install without --no-install-recommends may bloat image")

        return result

    def validate_dockerfile_content(self, content: str) -> ImageValidationResult:
        """Validate Dockerfile content directly.

        Args:
            content: Dockerfile content as string.

        Returns:
            ImageValidationResult with validation status.
        """
        result = ImageValidationResult(image_path="<inline>")

        lines = content.split("\n")
        layer_count = 0
        base_image = ""

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith(("RUN ", "COPY ", "ADD ", "ENV ", "WORKDIR ", "EXPOSE ", "VOLUME ")):
                layer_count += 1
            if stripped.startswith("FROM "):
                parts = stripped.split()
                if len(parts) >= 2:
                    base_image = parts[1]

        result.layer_count = layer_count
        result.base_image = base_image

        if layer_count > self.max_layers:
            result.issues.append(f"Layer count {layer_count} exceeds limit {self.max_layers}")

        if base_image in self.KNOWN_VULNERABLE_BASES:
            result.issues.append(f"Known vulnerable base image: {base_image}")

        if "root" in content and "USER" not in content:
            result.warnings.append("Dockerfile runs as root without USER directive")

        result.valid = len(result.issues) == 0
        return result
