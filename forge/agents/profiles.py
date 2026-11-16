"""Agent configuration profiles.

YAML-based configuration profiles for agent behavior (temperature, max tokens,
system prompts). Enables easy switching between different agent strategies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentProfile:
    """Configuration profile for an agent.

    Attributes:
        name: Profile name (e.g., "conservative", "aggressive").
        temperature: Sampling temperature for LLM agents.
        max_tokens: Maximum tokens per response.
        system_prompt: System prompt / instructions.
        max_steps: Maximum tool-call steps per run.
        tools: List of available tool names.
        metadata: Additional configuration.
    """

    name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = ""
    max_steps: int = 50
    tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "max_steps": self.max_steps,
            "tools": self.tools,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentProfile:
        return cls(
            name=data["name"],
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            system_prompt=data.get("system_prompt", ""),
            max_steps=data.get("max_steps", 50),
            tools=data.get("tools", []),
            metadata=data.get("metadata", {}),
        )


class ProfileManager:
    """Manages agent configuration profiles.

    Profiles are stored as YAML files in a configurable directory.
    """

    DEFAULT_PROFILES = {
        "conservative": {
            "name": "conservative",
            "temperature": 0.2,
            "max_tokens": 4096,
            "system_prompt": "You are a careful software engineer. Analyze the code thoroughly before making changes. Test each change incrementally.",
            "max_steps": 100,
            "tools": [
                "list_files",
                "read_file",
                "search_code",
                "write_file",
                "run_public_tests",
                "inspect_test_output",
                "inspect_git_diff",
                "finish_task",
            ],
        },
        "aggressive": {
            "name": "aggressive",
            "temperature": 0.9,
            "max_tokens": 2048,
            "system_prompt": "You are an innovative software engineer. Make bold changes to fix bugs quickly. Prioritize speed over perfection.",
            "max_steps": 30,
            "tools": ["list_files", "read_file", "write_file", "run_public_tests", "finish_task"],
        },
        "balanced": {
            "name": "balanced",
            "temperature": 0.7,
            "max_tokens": 4096,
            "system_prompt": "You are a skilled software engineer. Balance thoroughness with efficiency when fixing bugs.",
            "max_steps": 50,
            "tools": [
                "list_files",
                "read_file",
                "search_code",
                "write_file",
                "run_public_tests",
                "inspect_test_output",
                "inspect_git_diff",
                "finish_task",
            ],
        },
    }

    def __init__(self, profiles_dir: Path | None = None):
        """Initialize the profile manager.

        Args:
            profiles_dir: Directory to store profiles. Defaults to configs/agent_profiles/.
        """
        self.profiles_dir = profiles_dir or Path("configs/agent_profiles")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._defaults = {name: AgentProfile.from_dict(data) for name, data in self.DEFAULT_PROFILES.items()}

    def load_profile(self, name: str) -> AgentProfile | None:
        """Load a profile by name.

        Args:
            name: Profile name.

        Returns:
            AgentProfile if found, None otherwise.
        """
        # Check custom profiles first
        profile_file = self.profiles_dir / f"{name}.yaml"
        if profile_file.exists():
            data = yaml.safe_load(profile_file.read_text())
            return AgentProfile.from_dict(data)

        # Fall back to defaults
        if name in self._defaults:
            return self._defaults[name]

        return None

    def save_profile(self, profile: AgentProfile) -> Path:
        """Save a profile to disk.

        Args:
            profile: The profile to save.

        Returns:
            Path to the saved profile file.
        """
        profile_file = self.profiles_dir / f"{profile.name}.yaml"
        profile_file.write_text(yaml.dump(profile.to_dict(), default_flow_style=False))
        return profile_file

    def list_profiles(self) -> list[str]:
        """List all available profile names.

        Returns:
            List of profile names (custom + defaults).
        """
        custom = [f.stem for f in self.profiles_dir.glob("*.yaml")]
        all_profiles = list(dict.fromkeys(custom + list(self._defaults.keys())))
        return all_profiles

    def get_default(self, name: str = "balanced") -> AgentProfile:
        """Get a default profile.

        Args:
            name: Default profile name (conservative, aggressive, balanced).

        Returns:
            AgentProfile for the specified default.
        """
        return self._defaults.get(name, self._defaults["balanced"])
