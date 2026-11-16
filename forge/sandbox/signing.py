"""Container image signing for sandbox integrity.

Verifies sandbox container integrity using SHA-256 hashing of Dockerfile
and build context. Stores signatures in a JSON file for verification.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ImageSignature:
    """Signature for a container image."""

    image_path: str
    dockerfile_hash: str
    context_hash: str
    signed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "image_path": self.image_path,
            "dockerfile_hash": self.dockerfile_hash,
            "context_hash": self.context_hash,
            "signed_at": self.signed_at,
        }


class ImageSigner:
    """Signs and verifies container images using SHA-256 hashing.

    Provides simple hash-based signing for development integrity checks.
    Not cryptographic signatures — sufficient for detecting tampered images.
    """

    def __init__(self, signatures_path: str = "configs/sandbox_signatures.json"):
        """Initialize the image signer.

        Args:
            signatures_path: Path to store/load signatures JSON file.
        """
        self.signatures_path = Path(signatures_path)
        self._signatures: dict[str, ImageSignature] = {}
        self._load_signatures()

    def _load_signatures(self) -> None:
        """Load existing signatures from file."""
        if self.signatures_path.exists():
            try:
                data = json.loads(self.signatures_path.read_text(encoding="utf-8"))
                for path, sig_data in data.items():
                    self._signatures[path] = ImageSignature(**sig_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to load signatures: {e}")

    def _save_signatures(self) -> None:
        """Save signatures to file."""
        self.signatures_path.parent.mkdir(parents=True, exist_ok=True)
        data = {path: sig.to_dict() for path, sig in self._signatures.items()}
        self.signatures_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _hash_file(self, file_path: str | Path) -> str:
        """Compute SHA-256 hash of a file.

        Args:
            file_path: Path to the file.

        Returns:
            Hex digest string.
        """
        path = Path(file_path)
        if not path.exists():
            return ""
        h = hashlib.sha256()
        for chunk in iter(lambda: path.read_bytes()[0:8192], b""):
            h.update(chunk)
        return h.hexdigest()

    def sign(self, image_path: str | Path) -> ImageSignature:
        """Sign a container image by hashing its Dockerfile and context.

        Args:
            image_path: Path to the image directory containing Dockerfile.

        Returns:
            ImageSignature for the image.
        """
        path = Path(image_path)
        dockerfile = path / "Dockerfile"

        dockerfile_hash = self._hash_file(dockerfile) if dockerfile.exists() else ""

        # Hash all files in the context directory
        context_files = sorted(str(p) for p in path.rglob("*") if p.is_file())
        context_h = hashlib.sha256()
        for f in context_files:
            context_h.update(f.encode())
            context_h.update(self._hash_file(f).encode())
        context_hash = context_h.hexdigest()

        import datetime
        sig = ImageSignature(
            image_path=str(path),
            dockerfile_hash=dockerfile_hash,
            context_hash=context_hash,
            signed_at=datetime.datetime.now().isoformat(),
        )
        self._signatures[str(path)] = sig
        self._save_signatures()
        return sig

    def verify(self, image_path: str | Path) -> bool:
        """Verify a container image against its stored signature.

        Args:
            image_path: Path to the image directory.

        Returns:
            True if the image matches its signature, False otherwise.
        """
        path = str(Path(image_path))
        if path not in self._signatures:
            logger.warning(f"No signature found for {path}")
            return False

        sig = self._signatures[path]
        dockerfile = Path(image_path) / "Dockerfile"

        current_dockerfile_hash = self._hash_file(dockerfile) if dockerfile.exists() else ""
        if current_dockerfile_hash != sig.dockerfile_hash:
            logger.warning(f"Dockerfile hash mismatch for {path}")
            return False

        return True

    def list_signatures(self) -> list[ImageSignature]:
        """List all stored signatures.

        Returns:
            List of ImageSignature objects.
        """
        return list(self._signatures.values())

    def remove(self, image_path: str | Path) -> bool:
        """Remove a signature.

        Args:
            image_path: Path to the image directory.

        Returns:
            True if removed, False if not found.
        """
        path = str(Path(image_path))
        if path in self._signatures:
            del self._signatures[path]
            self._save_signatures()
            return True
        return False
