"""Agent configuration loading from environment variables and YAML.

Provides helper functions to create AgentConfig instances from
environment variables (FORGELAB_PROVIDER, FORGELAB_API_KEY, etc.)
or from YAML configuration files.
"""

from __future__ import annotations

import os
from typing import Any

from forge.core.schemas import AgentConfig


def load_agent_config_from_env(agent_type: str = "openai_compatible") -> AgentConfig:
    """Load agent configuration from environment variables.

    Reads the following environment variables:
    - FORGELAB_PROVIDER: API provider name (e.g. "openai")
    - FORGELAB_API_KEY: API key (not stored in config)
    - FORGELAB_BASE_URL: Custom API base URL
    - FORGELAB_MODEL: Model identifier
    - FORGELAB_MAX_STEPS: Maximum tool-call steps
    - FORGELAB_TEMPERATURE: Sampling temperature

    Args:
        agent_type: Type of agent to configure.

    Returns:
        AgentConfig instance populated from environment.
    """
    provider = os.environ.get("FORGELAB_PROVIDER", "openai")
    model = os.environ.get("FORGELAB_MODEL", "gpt-4")
    max_steps = int(os.environ.get("FORGELAB_MAX_STEPS", "50"))
    temperature = float(os.environ.get("FORGELAB_TEMPERATURE", "0.7"))

    metadata = {}
    base_url = os.environ.get("FORGELAB_BASE_URL")
    if base_url:
        metadata["base_url"] = base_url

    # Check if API key is available (don't store it in config)
    api_key = os.environ.get("FORGELAB_API_KEY")
    if api_key and agent_type == "openai_compatible":
        metadata["has_api_key"] = True
    else:
        metadata["has_api_key"] = False

    return AgentConfig(
        agent_type=agent_type,
        model=model,
        provider=provider,
        max_steps=max_steps,
        temperature=temperature,
        metadata=metadata,
    )


def create_mock_config(scenario: str = "success") -> AgentConfig:
    """Create a configuration for the MockAgent.

    Args:
        scenario: Mock scenario ("success", "partial", "failure", "no_change").

    Returns:
        AgentConfig for MockAgent.
    """
    return AgentConfig(
        agent_type="mock",
        metadata={"scenario": scenario, "is_simulation": True},
    )


def merge_agent_configs(
    base: AgentConfig,
    overrides: dict[str, Any],
) -> AgentConfig:
    """Merge a base config with override values.

    Args:
        base: Base configuration.
        overrides: Dictionary of values to override.

    Returns:
        New AgentConfig with merged values.
    """
    base_dict = base.to_dict()
    base_dict.update(overrides)
    return AgentConfig.from_dict(base_dict)
