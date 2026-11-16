"""Configuration management for ForgeLab.

Loads settings from YAML config files and environment variables,
with sensible defaults for development mode.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class Config:
    """Central configuration for ForgeLab.

    Reads from YAML config files and environment variables.
    Falls back to sensible defaults for development.

    Attributes:
        data: Merged configuration dictionary.
        config_dir: Path to the configs/ directory.
        base_dir: Project root directory.
    """

    def __init__(
        self,
        config_dir: str | None = None,
        base_dir: str | None = None,
    ):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent.parent
        self.config_dir = Path(config_dir) if config_dir else self.base_dir / "configs"
        self.data: dict[str, Any] = {}
        self._load_defaults()
        self._load_yaml()
        self._load_env()

    def _load_defaults(self) -> None:
        """Set default configuration values."""
        self.data = {
            "database": {
                "url": "sqlite:///./forgelab.db",
                "echo": False,
            },
            "sandbox": {
                "image": "forgelab/sandbox:python3.11",
                "memory_limit": "512m",
                "cpu_limit": 1.0,
                "timeout_seconds": 300,
                "network_disabled": True,
                "privileged": False,
            },
            "agent": {
                "max_steps": 50,
                "temperature": 0.7,
                "provider": os.getenv("FORGELAB_PROVIDER", "mock"),
                "model": os.getenv("FORGELAB_MODEL", ""),
                "api_key": os.getenv("FORGELAB_API_KEY", ""),
                "base_url": os.getenv("FORGELAB_BASE_URL", ""),
            },
            "curriculum": {
                "strategy": "adaptive",
                "min_samples_per_capability": 5,
                "max_difficulty_change": 1,
                "exploration_ratio": 0.2,
                "diversity_min": 3,
            },
            "world_factory": {
                "templates_dir": str(self.base_dir / "templates"),
                "output_dir": str(self.base_dir / "runs"),
            },
            "artifacts": {
                "runs_dir": str(self.base_dir / "runs"),
                "experiments_dir": str(self.base_dir / "experiments"),
                "datasets_dir": str(self.base_dir / "datasets"),
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "reload": True,
            },
        }

    def _load_yaml(self) -> None:
        """Load configuration from YAML files."""
        if not self.config_dir.exists():
            return

        for yaml_file in sorted(self.config_dir.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    file_data = yaml.safe_load(f) or {}
                self._deep_merge(self.data, file_data)
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")

        for yaml_file in sorted(self.config_dir.glob("*.yml")):
            try:
                with open(yaml_file) as f:
                    file_data = yaml.safe_load(f) or {}
                self._deep_merge(self.data, file_data)
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")

    def _load_env(self) -> None:
        """Override configuration with environment variables."""
        env_mappings = {
            "FORGELAB_DATABASE_URL": ("database", "url"),
            "FORGELAB_PROVIDER": ("agent", "provider"),
            "FORGELAB_API_KEY": ("agent", "api_key"),
            "FORGELAB_BASE_URL": ("agent", "base_url"),
            "FORGELAB_MODEL": ("agent", "model"),
            "FORGELAB_MAX_STEPS": ("agent", "max_steps"),
            "FORGELAB_SANDBOX_IMAGE": ("sandbox", "image"),
            "FORGELAB_LOG_LEVEL": ("logging", "level"),
        }

        for env_var, path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested(self.data, path, value)

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """Deep merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _set_nested(self, data: dict[str, Any], path: tuple, value: Any) -> None:
        """Set a value in a nested dictionary by path tuple."""
        current = data
        for part in path[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[path[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dotted key path.

        Args:
            key: Dotted key path, e.g. "database.url".
            default: Default value if key not found.

        Returns:
            The configuration value.
        """
        parts = key.split(".")
        current = self.data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def get_section(self, section: str) -> dict[str, Any]:
        """Get an entire configuration section.

        Args:
            section: Section name, e.g. "database".

        Returns:
            The section dictionary, or empty dict if not found.
        """
        return self.data.get(section, {})

    def to_dict(self) -> dict[str, Any]:
        """Return the full configuration as a dictionary."""
        return dict(self.data)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

_default_config: Config | None = None


def load_config(
    config_dir: str | None = None,
    base_dir: str | None = None,
) -> Config:
    """Load and return a Config instance.

    This is a convenience function that creates a new Config object
    with the specified directories. Use this when you need a fresh
    config or want to override the default paths.

    Args:
        config_dir: Path to the configs/ directory.
        base_dir: Project root directory.

    Returns:
        A configured Config instance.
    """
    return Config(config_dir=config_dir, base_dir=base_dir)


def get_config() -> Config:
    """Return the global Config singleton.

    Loads configuration once on first call and reuses it.
    Precedence: environment variables > YAML config files > defaults.

    Returns:
        The global Config instance.
    """
    global _default_config
    if _default_config is None:
        _default_config = Config()
    return _default_config
